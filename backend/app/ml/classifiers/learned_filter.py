"""
Learned Filter — Self-learning email classifier
Trains on user confirm/reject decisions using TF-IDF + Logistic Regression.
Activates after MIN_EXAMPLES labeled examples are available.
"""

import logging
import threading
from typing import Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Minimum labeled examples before the model activates
MIN_EXAMPLES = 30

# Confidence threshold — only use learned model if it's this confident
CONFIDENCE_THRESHOLD = 0.75


class LearnedFilter:
    """
    Global TF-IDF + Logistic Regression classifier.
    Trains on all users' confirm/reject decisions.
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
    """
    from app.database import async_session_maker
    from app.models.training_example import TrainingExample
    from sqlalchemy import select

    async with async_session_maker() as db:
        result = await db.execute(
            select(TrainingExample.email_subject, TrainingExample.email_snippet,
                   TrainingExample.email_from, TrainingExample.label)
        )
        rows = result.all()

    if len(rows) < MIN_EXAMPLES:
        logger.info(f"[LEARNED] {len(rows)} examples — need {MIN_EXAMPLES} to train")
        return

    texts = [f"{r[0] or ''} {r[1] or ''} {r[2] or ''}" for r in rows]
    labels = [r[3] for r in rows]

    learned_filter.train(texts, labels)
