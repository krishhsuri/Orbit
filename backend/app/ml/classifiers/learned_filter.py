"""
Learned Filter — Self-learning email classifier
Trains on user confirm/reject decisions using TF-IDF + Logistic Regression.
Activates after MIN_EXAMPLES labeled examples are available.

Fix #3: Anti-poisoning guardrails added:
- Max 50 examples per user (prevents one user flooding the dataset)
- Training requires at least 2 distinct users
- Users whose label distribution deviates >80% from global average are downweighted
"""

import logging
import threading
from collections import Counter, defaultdict
from typing import Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Minimum labeled examples before the model activates
MIN_EXAMPLES = 30

# Confidence threshold — only use learned model if it's this confident
CONFIDENCE_THRESHOLD = 0.75

# Anti-poisoning constants
MAX_EXAMPLES_PER_USER = 50          # Cap any single user's contribution
MIN_UNIQUE_USERS = 2                 # Require at least 2 distinct users
OUTLIER_DEVIATION_THRESHOLD = 0.80  # If one user's positives are >80% deviant, downweight


def _apply_anti_poisoning_guardrails(rows: list) -> list:
    """
    Apply anti-poisoning rules to training data rows.

    Args:
        rows: list of (subject, snippet, email_from, label, user_id) tuples

    Returns:
        Filtered/capped list of rows.
    """
    if not rows:
        return rows

    # Count distinct users
    user_ids = {r[4] for r in rows}
    if len(user_ids) < MIN_UNIQUE_USERS:
        logger.info(
            f"[LEARNED] Only {len(user_ids)} distinct user(s) — need {MIN_UNIQUE_USERS} to train safely"
        )
        return []  # Refuse to train on data from a single user

    # Cap per-user contribution
    user_row_counts: dict = defaultdict(list)
    for r in rows:
        user_row_counts[str(r[4])].append(r)

    capped_rows = []
    for uid, user_rows in user_row_counts.items():
        if len(user_rows) > MAX_EXAMPLES_PER_USER:
            logger.info(
                f"[LEARNED] User {uid}: capping {len(user_rows)} → {MAX_EXAMPLES_PER_USER} examples"
            )
            # Keep most recent; rows should already be ordered by created_at desc
            user_rows = user_rows[:MAX_EXAMPLES_PER_USER]
        capped_rows.extend(user_rows)

    # Outlier dampening: compute global positive rate, then check per-user
    global_labels = [r[3] for r in capped_rows]
    global_positive_rate = global_labels.count("positive") / max(len(global_labels), 1)

    kept_rows = []
    for uid, user_rows in defaultdict(list, {
        str(r[4]): [r for r in capped_rows if str(r[4]) == str(uid)]
        for r in capped_rows
    }).items():
        user_labels = [r[3] for r in user_rows]
        user_positive_rate = user_labels.count("positive") / max(len(user_labels), 1)

        deviation = abs(user_positive_rate - global_positive_rate)
        if deviation >= OUTLIER_DEVIATION_THRESHOLD:
            # Downweight by keeping only half of their examples
            half = max(1, len(user_rows) // 2)
            logger.warning(
                f"[LEARNED] User {uid} is an outlier (deviation={deviation:.2f}). "
                f"Keeping {half}/{len(user_rows)} examples."
            )
            kept_rows.extend(user_rows[:half])
        else:
            kept_rows.extend(user_rows)

    return kept_rows


class LearnedFilter:
    """
    Global TF-IDF + Logistic Regression classifier.
    Trains on all users' confirm/reject decisions with anti-poisoning guardrails.
    Thread-safe with a lock for model retraining.
    """

    def __init__(self):
        self._model: Optional[Pipeline] = None
        self._lock = threading.Lock()
        self._example_count = 0

    def train(self, texts: list[str], labels: list[str]) -> bool:
        """
        Train the model on labeled examples.
        Returns True if training succeeded, False if not enough data.
        """
        if len(texts) < MIN_EXAMPLES:
            logger.info(
                f"[LEARNED] Not enough examples ({len(texts)}/{MIN_EXAMPLES}), skipping training"
            )
            return False

        with self._lock:
            try:
                pipeline = Pipeline([
                    ("tfidf", TfidfVectorizer(
                        max_features=5000,
                        ngram_range=(1, 2),
                        stop_words="english",
                        min_df=2,
                    )),
                    ("clf", LogisticRegression(
                        max_iter=1000,
                        C=1.0,
                        class_weight="balanced",
                    )),
                ])
                pipeline.fit(texts, labels)
                self._model = pipeline
                self._example_count = len(texts)
                logger.info(
                    f"[LEARNED] Model trained on {len(texts)} examples"
                )
                return True
            except Exception as e:
                logger.error(f"[LEARNED] Training failed: {e}")
                return False

    def predict(self, subject: str, snippet: str, sender: str) -> Tuple[Optional[str], float]:
        """
        Predict whether an email is job-related.
        Returns (label, confidence) or (None, 0.0) if model not ready.
        """
        if self._model is None:
            return None, 0.0

        text = f"{subject} {snippet} {sender}"

        with self._lock:
            try:
                proba = self._model.predict_proba([text])[0]
                classes = self._model.classes_
                max_idx = proba.argmax()
                label = classes[max_idx]
                confidence = float(proba[max_idx])
                return label, confidence
            except Exception as e:
                logger.error(f"[LEARNED] Prediction failed: {e}")
                return None, 0.0

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def example_count(self) -> int:
        return self._example_count


# Singleton instance — shared across the application
learned_filter = LearnedFilter()


async def refresh_learned_model():
    """
    Reload training data from DB and retrain the model.
    Call this after new training examples are added.

    Fix #3: Applies anti-poisoning guardrails before training:
    - Caps each user to MAX_EXAMPLES_PER_USER examples
    - Refuses to train if fewer than MIN_UNIQUE_USERS distinct users
    - Downweights outlier users whose label distribution deviates heavily
    """
    from app.database import async_session_maker
    from app.models.training_example import TrainingExample
    from sqlalchemy import select

    async with async_session_maker() as db:
        result = await db.execute(
            select(
                TrainingExample.email_subject,
                TrainingExample.email_snippet,
                TrainingExample.email_from,
                TrainingExample.label,
                TrainingExample.user_id,
            ).order_by(TrainingExample.created_at.desc())  # Newest first (for capping)
        )
        rows = result.all()

    if len(rows) < MIN_EXAMPLES:
        logger.info(f"[LEARNED] {len(rows)} examples — need {MIN_EXAMPLES} to train")
        return

    # Apply anti-poisoning guardrails (Fix #3)
    safe_rows = _apply_anti_poisoning_guardrails(list(rows))
    if not safe_rows:
        logger.warning("[LEARNED] Anti-poisoning guardrails rejected all training data")
        return

    if len(safe_rows) < MIN_EXAMPLES:
        logger.info(f"[LEARNED] Only {len(safe_rows)} safe examples after guardrails — need {MIN_EXAMPLES}")
        return

    texts = [f"{r[0] or ''} {r[1] or ''} {r[2] or ''}" for r in safe_rows]
    labels = [r[3] for r in safe_rows]

    learned_filter.train(texts, labels)
    logger.info(f"[LEARNED] Retrained on {len(safe_rows)} safe examples (from {len(rows)} total)")
