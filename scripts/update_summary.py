#!/usr/bin/env python3
"""Rebuild CURRENT-STATE.json from append-only workout sessions."""
import json
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import atomic_write, load_json, resolve_user_data
from coach_rules import recommend_exercise

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = resolve_user_data(ROOT)
CN_TZ = timezone(timedelta(hours=8))


def load_all_sessions():
    directory = USER_DATA / "sessions"
    if not directory.exists():
        return []
    sessions = []
    for path in sorted(directory.glob("*.json")):
        try:
            sessions.append(load_json(path))
        except Exception as error:
            print(f"[WARN] 跳过 {path.name}: {error}")
    return sorted(sessions, key=lambda item: item.get("date", ""))


def days_since(date_text):
    today = datetime.now(CN_TZ).date()
    date = datetime.strptime(date_text, "%Y-%m-%d").date()
    return (today - date).days


def comparison_key(exercise):
    equipment = exercise.get("equipment")
    settings = exercise.get("settings", {})
    return equipment, json.dumps(settings, ensure_ascii=False, sort_keys=True)


def collect_occurrences(sessions):
    grouped = defaultdict(list)
    for session in sessions:
        date = session.get("date")
        for exercise in session.get("exercises", []):
            name = exercise.get("exercise")
            if not name:
                continue
            item = deepcopy(exercise)
            item["date"] = date
            grouped[name].append(item)
    return grouped


def comparable_completed_history(occurrences):
    completed = [
        item for item in occurrences
        if item.get("status", "completed") == "completed"
    ]
    if not completed:
        return []
    latest_key = comparison_key(completed[-1])
    comparable = [item for item in completed if comparison_key(item) == latest_key]
    return comparable[-3:]


def compute_recovery(sessions, occurrences):
    if not sessions:
        return {
            "last_session_date": None,
            "days_since_last": None,
            "recent_rpe_trend": [],
            "active_pain": [],
        }
    last_date = sessions[-1].get("date")
    recent_rpe = [
        item["overall_rpe"]
        for item in sessions[-5:]
        if item.get("overall_rpe") is not None
    ]
    active_pain = []
    for name, items in sorted(occurrences.items()):
        latest = items[-1]
        pain = latest.get("pain", {})
        severity = pain.get("severity", 0) or 0
        if severity > 0:
            active_pain.append({
                "exercise": name,
                "location": pain.get("location"),
                "severity": severity,
                "date": latest.get("date"),
            })
    return {
        "last_session_date": last_date,
        "days_since_last": days_since(last_date),
        "recent_rpe_trend": recent_rpe,
        "active_pain": active_pain,
    }


def build_state(old_state, sessions):
    occurrences = collect_occurrences(sessions)
    history = {}
    recommendations = {}
    for name, items in sorted(occurrences.items()):
        comparable = comparable_completed_history(items)
        if not comparable:
            continue
        history[name] = comparable
        exercise_gap = days_since(comparable[-1]["date"])
        recommendations[name] = recommend_exercise(comparable, exercise_gap)

    name = old_state.get("profile", {}).get("name", "<你的名字>")
    return {
        "schema_version": "2.0",
        "updated_at": datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "profile": {"name": name, "mode": "pure_coach"},
        "recovery": compute_recovery(sessions, occurrences),
        "exercise_history": history,
        "next_recommendations": recommendations,
    }


def main():
    state_file = USER_DATA / "CURRENT-STATE.json"
    if not state_file.exists():
        print(f"[ERROR] {state_file} 不存在。先运行 init_profile.py。")
        return 1
    old_state = load_json(state_file)
    state = build_state(old_state, load_all_sessions())
    atomic_write(state_file, state)
    print(f"[OK] 已更新 {state_file.name}")
    print(f"   已汇总 {len(state['exercise_history'])} 个可比较动作。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
