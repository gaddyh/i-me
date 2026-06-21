# scripts/evaluate_reminders.py

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dspy

from app.agent.dspy_config import configure_dspy_once
from app.agent.single_turn_agent import WhatsAppSingleTurnAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("greenapi-bot")


@dataclass
class EvalResult:
    id: str
    score: float
    selected_fn_ok: bool
    args_ok: bool
    missing_fields_ok: bool
    forbidden_ok: bool
    expected_selected_fn: str
    actual_selected_fn: str
    expected_args: dict[str, Any]
    actual_args: dict[str, Any]
    expected_missing_fields: list[str]
    actual_missing_fields: list[str]
    notes: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {e}") from e

    return rows


def make_dspy_examples(rows: list[dict[str, Any]]) -> list[dspy.Example]:
    examples = []

    for row in rows:
        inp = row["input"]

        ex = dspy.Example(
            id=row["id"],
            user_input=inp["user_input"],
            now=inp["now"],
            timezone=inp.get("timezone", "Asia/Jerusalem"),
            expected_selected_fn=row["expected_selected_fn"],
            expected_args=row.get("expected_args", {}),
            expected_missing_fields=row.get("expected_missing_fields", []),
            forbidden_functions=row.get("forbidden_functions", []),
            tags=row.get("tags", []),
            notes=row.get("notes", ""),
        ).with_inputs("user_input", "now", "timezone")

        examples.append(ex)

    return examples


def normalize_string(value: Any) -> str:
    return str(value).strip()


def normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item).strip() for item in value)


def expected_args_match(
    expected_args: dict[str, Any],
    actual_args: dict[str, Any],
) -> bool:
    """
    Partial exact match.

    If expected_args says:
      {"missing_fields": ["remind_time"]}

    Then the model may also include:
      {"question": "...", "missing_fields": ["remind_time"]}

    and still pass.
    """
    if not isinstance(actual_args, dict):
        return False

    for key, expected_value in expected_args.items():
        if key not in actual_args:
            return False

        actual_value = actual_args[key]

        if isinstance(expected_value, list):
            if normalize_list(expected_value) != normalize_list(actual_value):
                return False
        else:
            if normalize_string(expected_value) != normalize_string(actual_value):
                return False

    return True


def get_actual_missing_fields(prediction: dspy.Prediction) -> list[str]:
    args = getattr(prediction, "args", {}) or {}

    if not isinstance(args, dict):
        return []

    return normalize_list(args.get("missing_fields", []))


def basic_reminder_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace=None,
) -> float:
    selected_fn_ok = (
        normalize_string(getattr(prediction, "selected_fn", ""))
        == normalize_string(example.expected_selected_fn)
    )

    actual_args = getattr(prediction, "args", {}) or {}
    args_ok = expected_args_match(example.expected_args, actual_args)

    expected_missing = normalize_list(example.expected_missing_fields)
    actual_missing = get_actual_missing_fields(prediction)
    missing_fields_ok = expected_missing == actual_missing

    forbidden_functions = set(example.forbidden_functions or [])
    actual_selected_fn = normalize_string(getattr(prediction, "selected_fn", ""))
    forbidden_ok = actual_selected_fn not in forbidden_functions

    # Simple weighted score.
    # Tool choice matters most. Then forbidden action safety. Then args.
    score = 0.0
    score += 0.45 if selected_fn_ok else 0.0
    score += 0.25 if args_ok else 0.0
    score += 0.20 if forbidden_ok else 0.0
    score += 0.10 if missing_fields_ok else 0.0

    return score


def evaluate_rows(
    agent: WhatsAppSingleTurnAgent,
    examples: list[dspy.Example],
) -> list[EvalResult]:
    results = []

    for ex in examples:
        pred = agent(
            user_input=ex.user_input,
            now=ex.now,
            timezone=ex.timezone,
        )

        selected_fn_ok = (
            normalize_string(pred.selected_fn)
            == normalize_string(ex.expected_selected_fn)
        )

        args_ok = expected_args_match(ex.expected_args, pred.args)

        expected_missing = normalize_list(ex.expected_missing_fields)
        actual_missing = get_actual_missing_fields(prediction=pred)
        missing_fields_ok = expected_missing == actual_missing

        forbidden_ok = normalize_string(pred.selected_fn) not in set(
            ex.forbidden_functions or []
        )

        score = basic_reminder_metric(ex, pred)

        results.append(
            EvalResult(
                id=ex.id,
                score=score,
                selected_fn_ok=selected_fn_ok,
                args_ok=args_ok,
                missing_fields_ok=missing_fields_ok,
                forbidden_ok=forbidden_ok,
                expected_selected_fn=ex.expected_selected_fn,
                actual_selected_fn=pred.selected_fn,
                expected_args=ex.expected_args,
                actual_args=pred.args,
                expected_missing_fields=expected_missing,
                actual_missing_fields=actual_missing,
                notes=ex.notes,
            )
        )

    return results


def print_summary(results: list[EvalResult]) -> None:
    total = len(results)

    if total == 0:
        print("No examples.")
        return

    avg_score = sum(r.score for r in results) / total

    selected_fn_acc = sum(r.selected_fn_ok for r in results) / total
    args_acc = sum(r.args_ok for r in results) / total
    missing_acc = sum(r.missing_fields_ok for r in results) / total
    forbidden_acc = sum(r.forbidden_ok for r in results) / total

    exact_pass = sum(
        r.selected_fn_ok and r.args_ok and r.missing_fields_ok and r.forbidden_ok
        for r in results
    ) / total

    print("\n=== SUMMARY ===")
    print(f"Examples:              {total}")
    print(f"Average score:         {avg_score:.3f}")
    print(f"Exact pass rate:       {exact_pass:.3f}")
    print(f"Selected fn accuracy:  {selected_fn_acc:.3f}")
    print(f"Args accuracy:         {args_acc:.3f}")
    print(f"Missing fields acc:    {missing_acc:.3f}")
    print(f"Forbidden fn safety:   {forbidden_acc:.3f}")


def print_failures(results: list[EvalResult], max_failures: int) -> None:
    failures = [
        r
        for r in results
        if not (
            r.selected_fn_ok
            and r.args_ok
            and r.missing_fields_ok
            and r.forbidden_ok
        )
    ]

    if not failures:
        print("\nNo failures 🎉")
        return

    print(f"\n=== FAILURES showing {min(len(failures), max_failures)} of {len(failures)} ===")

    for r in failures[:max_failures]:
        print("\n---")
        print(f"id: {r.id}")
        print(f"score: {r.score:.3f}")
        print(f"notes: {r.notes}")

        print(f"expected_selected_fn: {r.expected_selected_fn}")
        print(f"actual_selected_fn:   {r.actual_selected_fn}")
        print(f"selected_fn_ok:       {r.selected_fn_ok}")
        print(f"forbidden_ok:         {r.forbidden_ok}")

        print("expected_args:")
        print(json.dumps(r.expected_args, ensure_ascii=False, indent=2))

        print("actual_args:")
        print(json.dumps(r.actual_args, ensure_ascii=False, indent=2))

        print(f"args_ok:              {r.args_ok}")

        print(f"expected_missing:     {r.expected_missing_fields}")
        print(f"actual_missing:       {r.actual_missing_fields}")
        print(f"missing_fields_ok:    {r.missing_fields_ok}")


def save_results(path: Path, results: list[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "id": r.id,
                        "score": r.score,
                        "selected_fn_ok": r.selected_fn_ok,
                        "args_ok": r.args_ok,
                        "missing_fields_ok": r.missing_fields_ok,
                        "forbidden_ok": r.forbidden_ok,
                        "expected_selected_fn": r.expected_selected_fn,
                        "actual_selected_fn": r.actual_selected_fn,
                        "expected_args": r.expected_args,
                        "actual_args": r.actual_args,
                        "expected_missing_fields": r.expected_missing_fields,
                        "actual_missing_fields": r.actual_missing_fields,
                        "notes": r.notes,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        default="data/reminders/dev.jsonl",
        help="Path to reminder eval JSONL.",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--out",
        default="runs/reminders/dev_results.jsonl",
    )
    args = parser.parse_args()

    configure_dspy_once()

    rows = load_jsonl(Path(args.data))
    examples = make_dspy_examples(rows)

    agent = WhatsAppSingleTurnAgent(max_steps=1)

    results = evaluate_rows(agent, examples)

    print_summary(results)
    print_failures(results, max_failures=args.max_failures)
    save_results(Path(args.out), results)

    print(f"\nSaved results to: {args.out}")


if __name__ == "__main__":
    main()