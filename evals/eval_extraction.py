"""
Run action-extraction evals against a labelled corpus.

Usage (from repo root):
  python evals/data/generate.py
  python evals/eval_extraction.py --corpus evals/data/corpus.json --action-positive-only
  python evals/eval_extraction.py --corpus evals/data/corpus_stale.json --offline

Live evals set LLM_MAX_RETRIES=1 so rate-limit failures exit in seconds, not minutes.
Use --checkpoint to resume after Groq quota resets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
except ImportError:
    pass

from evals.data.labels import (
    base_id,
    expected_actions,
    expected_is_job_related,
    extract_predicted_action_types,
)
from evals.metrics import EvalResult, update_result


def _result_payload(
    corpus_path: Path,
    result: EvalResult,
    *,
    elapsed: float,
    completed_ids: list[str],
    stopped_early: str | None = None,
) -> dict:
    payload = {
        "corpus": str(corpus_path),
        "emails_evaluated": result.emails_evaluated,
        "completed_ids": completed_ids,
        "elapsed_seconds": round(elapsed, 2),
        "micro_precision": round(result.micro_precision, 4),
        "micro_recall": round(result.micro_recall, 4),
        "micro_f1": round(result.micro_f1, 4),
        "job_related_errors": result.job_related_errors,
        "per_type": {
            action_type: {
                "precision": round(metrics.precision, 4),
                "recall": round(metrics.recall, 4),
                "f1": round(metrics.f1, 4),
                "tp": metrics.true_positive,
                "fp": metrics.false_positive,
                "fn": metrics.false_negative,
            }
            for action_type, metrics in sorted(result.per_type.items())
        },
        "confusion": {
            expected: dict(predicted_counts)
            for expected, predicted_counts in sorted(result.confusion.items())
        },
        "failures": result.failures,
    }
    if stopped_early:
        payload["stopped_early"] = stopped_early
    return payload


def _write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_offline_validation(corpus_path: Path) -> dict:
    """Validate corpus labels without calling Groq."""
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    emails = corpus["emails"]
    action_positive = sum(1 for e in emails if e.get("expected_actions"))
    by_prefix: dict[str, int] = {}
    for email in emails:
        bid = base_id(email["id"])
        prefix = bid.split("_")[0]
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

    return {
        "corpus": str(corpus_path),
        "mode": "offline",
        "email_count": len(emails),
        "action_positive_count": action_positive,
        "prefix_counts": dict(sorted(by_prefix.items())),
        "generated_at": corpus.get("generated_at"),
        "preserve_original_dates": corpus.get("preserve_original_dates"),
    }


async def run_eval(
    corpus_path: Path,
    *,
    limit: int | None = None,
    action_positive_only: bool = False,
    sleep_seconds: float = 15.0,
    min_confidence: float = 0.4,
    disable_audit: bool = True,
    checkpoint_path: Path | None = None,
    stop_on_rate_limit: bool = True,
) -> dict:
    from app.config import get_settings
    from app.llm.errors import LLMUnavailable
    from app.ml.llm.groq_client import GroqClient

    if disable_audit:
        os.environ["LLM_AUDIT_ENABLED"] = "false"
    os.environ.setdefault("LLM_MAX_RETRIES", "1")
    get_settings.cache_clear()

    settings = get_settings()
    if not settings.groq_api_key:
        raise SystemExit("GROQ_API_KEY is required to run live extraction evals.")

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    emails = corpus["emails"]
    if action_positive_only:
        emails = [e for e in emails if e.get("expected_actions")]
    if limit is not None:
        emails = emails[:limit]

    completed_ids: set[str] = set()
    if checkpoint_path and checkpoint_path.exists():
        prior = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        completed_ids = set(prior.get("completed_ids") or [])

    client = GroqClient(api_key=settings.groq_api_key)
    result = EvalResult()
    started = time.perf_counter()
    stopped_early: str | None = None

    for email in emails:
        email_id = email["id"]
        if email_id in completed_ids:
            continue

        bid = base_id(email_id)
        body = email.get("body_preview") or email.get("snippet") or ""
        expected = email.get("expected_actions") or expected_actions(bid)
        expected_job = email.get("expected_is_job_related")
        if expected_job is None:
            expected_job = expected_is_job_related(bid)

        try:
            raw = await client.extract_actions_from_email(
                subject=email.get("subject", ""),
                body=body,
                email_timestamp=email.get("date"),
            )
        except LLMUnavailable as exc:
            msg = str(exc)
            result.failures.append(
                {
                    "email_id": email_id,
                    "kind": "llm_error",
                    "error": type(exc).__name__,
                    "message": msg,
                }
            )
            if stop_on_rate_limit and ("429" in msg or "rate limit" in msg.lower()):
                stopped_early = "groq_rate_limit"
                if checkpoint_path:
                    payload = _result_payload(
                        corpus_path,
                        result,
                        elapsed=time.perf_counter() - started,
                        completed_ids=sorted(completed_ids),
                        stopped_early=stopped_early,
                    )
                    _write_checkpoint(checkpoint_path, payload)
                raise SystemExit(
                    "Groq rate limit hit — no quota left. "
                    f"Processed {len(completed_ids)} emails before stop. "
                    "Wait for quota reset (~1 hour), then re-run with the same --checkpoint path."
                ) from exc
            raw = None
        except Exception as exc:
            result.failures.append(
                {
                    "email_id": email_id,
                    "kind": "llm_error",
                    "error": type(exc).__name__,
                    "message": str(exc),
                }
            )
            raw = None

        predicted_job = bool(raw and raw.get("is_job_related"))
        predicted = extract_predicted_action_types(raw, min_confidence=min_confidence)

        update_result(
            result,
            email_id=email_id,
            expected=expected,
            predicted=predicted,
            expected_job_related=expected_job,
            predicted_job_related=predicted_job,
        )
        completed_ids.add(email_id)

        if checkpoint_path:
            payload = _result_payload(
                corpus_path,
                result,
                elapsed=time.perf_counter() - started,
                completed_ids=sorted(completed_ids),
            )
            _write_checkpoint(checkpoint_path, payload)

        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)

    return _result_payload(
        corpus_path,
        result,
        elapsed=time.perf_counter() - started,
        completed_ids=sorted(completed_ids),
        stopped_early=stopped_early,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate action extraction")
    parser.add_argument("--corpus", type=Path, default=EVALS_ROOT / "data" / "corpus.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--action-positive-only", action="store_true")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=15.0,
        help="Pause between live API calls (default 15s to stay under Groq TPM)",
    )
    parser.add_argument("--min-confidence", type=float, default=0.4)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Save/resume progress after each email",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Validate corpus only — no Groq calls",
    )
    args = parser.parse_args()

    if args.offline:
        payload = run_offline_validation(args.corpus)
    else:
        payload = asyncio.run(
            run_eval(
                args.corpus,
                limit=args.limit,
                action_positive_only=args.action_positive_only,
                sleep_seconds=args.sleep_seconds,
                min_confidence=args.min_confidence,
                checkpoint_path=args.checkpoint,
            )
        )

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    out = args.output or args.checkpoint
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
