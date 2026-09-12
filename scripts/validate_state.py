#!/usr/bin/env python3
"""Validate the pure-coach state and workout sessions without writing files."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_json, resolve_user_data

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = resolve_user_data(ROOT)


def validate_date(value, label, errors):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        errors.append(f"{label} 日期无效: {value}")


def validate_session(session, filename, errors):
    validate_date(session.get("date"), filename, errors)
    overall_rpe = session.get("overall_rpe")
    if overall_rpe is not None and not 1 <= overall_rpe <= 10:
        errors.append(f"{filename} overall_rpe 必须为 1-10")
    for exercise in session.get("exercises", []):
        name = exercise.get("exercise", "?")
        for index, item in enumerate(exercise.get("sets", []), start=1):
            rpe = item.get("rpe")
            rir = item.get("rir")
            if rpe is not None and not 1 <= rpe <= 10:
                errors.append(f"{filename} {name} 第{index}组 rpe 必须为 1-10")
            if rir is not None and not 0 <= rir <= 10:
                errors.append(f"{filename} {name} 第{index}组 rir 必须为 0-10")
        pain = exercise.get("pain", {})
        severity = pain.get("severity", 0)
        if severity is not None and not 0 <= severity <= 10:
            errors.append(f"{filename} {name} 疼痛程度必须为 0-10")


def main():
    errors = []
    state_file = USER_DATA / "CURRENT-STATE.json"
    if not state_file.exists():
        print("[ERROR] CURRENT-STATE.json 不存在。先运行 init_profile.py。")
        return 1
    try:
        state = load_json(state_file)
    except Exception as error:
        print(f"[ERROR] CURRENT-STATE.json 格式错误: {error}")
        return 1

    for key in (
        "schema_version",
        "profile",
        "recovery",
        "exercise_history",
        "next_recommendations",
    ):
        if key not in state:
            errors.append(f"CURRENT-STATE.json 缺少 {key}")
    if state.get("profile", {}).get("mode") != "pure_coach":
        errors.append("profile.mode 必须为 pure_coach")
    days_since_last = state.get("recovery", {}).get("days_since_last")
    if days_since_last is not None and days_since_last < 0:
        errors.append("recovery.days_since_last 不能为负数")

    sessions_dir = USER_DATA / "sessions"
    if sessions_dir.exists():
        for path in sorted(sessions_dir.glob("*.json")):
            try:
                session = load_json(path)
            except Exception as error:
                errors.append(f"{path.name} 格式错误: {error}")
                continue
            validate_session(session, path.name, errors)

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] 档案、状态和训练记录格式有效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
