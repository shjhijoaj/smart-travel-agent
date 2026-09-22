"""Offline checks for the two documented workflow cases.

This script deliberately uses only the standard library, so the test data and
basic validation can be checked before installing the API dependencies.
"""

import json
from pathlib import Path


ROOT = Path(__file__).parent
REQUIRED = {"departure", "destination", "travel_dates", "budget", "companions", "preferences", "language"}


def validate_case(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED - payload.keys())
    empty = sorted(key for key in REQUIRED if not str(payload.get(key, "")).strip())
    errors = []
    if missing:
        errors.append(f"缺少字段: {', '.join(missing)}")
    if empty:
        errors.append(f"字段为空: {', '.join(empty)}")
    try:
        budget = float(payload["budget"])
        if budget <= 0:
            errors.append("预算必须大于 0")
    except (KeyError, TypeError, ValueError):
        errors.append("预算必须是数字或数字文本")
    return errors


def main() -> int:
    failed = False
    for filename in ("normal-case.json", "budget-overflow.json"):
        errors = validate_case(ROOT / filename)
        if errors:
            failed = True
            print(f"FAIL {filename}: {'; '.join(errors)}")
        else:
            print(f"PASS {filename}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
