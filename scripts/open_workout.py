#!/usr/bin/env python3
"""Open the validated Active Workout in the operating system's default browser."""
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_workout import load_workout, validate_workout

ROOT = Path(__file__).resolve().parent.parent
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)


def validate_active_workout():
    workout_path = VISUALIZER / "current-workout.js"
    if not workout_path.exists():
        raise ValueError("current-workout.js 不存在")
    workout = load_workout(workout_path)
    errors = validate_workout(workout)
    if errors:
        raise ValueError("；".join(errors))
    return workout["sessionId"]


def build_workout_url(index_path, session_id):
    return index_path.resolve().as_uri() + "?" + urlencode({"session": session_id})


def main():
    index_path = VISUALIZER / "index.html"
    if not index_path.exists():
        print("[ERROR] 训练页 index.html 不存在")
        return 1

    try:
        session_id = validate_active_workout()
    except ValueError as error:
        print(f"[ERROR] {error}")
        return 1

    url = build_workout_url(index_path, session_id)
    if not webbrowser.open(url, new=2):
        print(f"[ERROR] 默认浏览器未能打开训练页：{url}")
        return 1

    print(f"[OK] 已在默认浏览器打开 Active Workout：{session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
