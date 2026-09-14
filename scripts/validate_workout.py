#!/usr/bin/env python3
"""Validate the generated Active Workout card before it is opened."""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)


def load_workout(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.CURRENT_WORKOUT\s*=\s*Object\.freeze\(\s*(\{.*\})\s*\)\s*;",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("current-workout.js 必须把合法 JSON 赋给 window.CURRENT_WORKOUT")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ValueError(f"current-workout.js 的 JSON 格式错误: {error.msg}")


def validate_workout(workout):
    errors = []
    if workout.get("schemaVersion") != "2.0":
        errors.append("schemaVersion 必须为 2.0")
    if workout.get("initialized") is not True:
        errors.append("initialized 必须为 true")

    for key in ("sessionId", "generatedAt", "planLabel", "name", "status"):
        if not isinstance(workout.get(key), str) or not workout[key].strip():
            errors.append(f"{key} 不能为空")

    generated_at = workout.get("generatedAt")
    if isinstance(generated_at, str) and generated_at.strip():
        try:
            generated_datetime = datetime.fromisoformat(generated_at)
        except ValueError:
            errors.append("generatedAt 必须是 ISO 8601 时间")
        else:
            if generated_datetime.tzinfo is not None:
                generated_date = generated_datetime.astimezone().date()
            else:
                generated_date = generated_datetime.date()
            if generated_date != datetime.now().astimezone().date():
                errors.append("generatedAt 必须是今天")

    notes = workout.get("notes")
    if not isinstance(notes, list):
        errors.append("notes 必须是数组")
    elif not all(isinstance(note, str) for note in notes):
        errors.append("notes 只能包含字符串")

    exercises = workout.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        errors.append("exercises 必须至少包含一个动作")
        return errors

    for index, exercise in enumerate(exercises, start=1):
        if not isinstance(exercise, dict):
            errors.append(f"第{index}个动作格式错误")
            continue

        order = exercise.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order <= 0:
            errors.append(f"第{index}个动作 order 必须为正整数")
        if not isinstance(exercise.get("name"), str) or not exercise["name"].strip():
            errors.append(f"第{index}个动作 name 不能为空")

        prescription = exercise.get("prescription")
        if not isinstance(prescription, dict):
            errors.append(f"第{index}个动作 prescription 格式错误")
            continue

        sets = prescription.get("sets")
        if not isinstance(sets, (int, float)) or isinstance(sets, bool) or sets <= 0:
            errors.append(f"第{index}个动作 prescription.sets 必须大于 0")
        for key in ("reps", "rpe"):
            value = prescription.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"第{index}个动作 prescription.{key} 不能为空")

        exercise_notes = exercise.get("notes")
        if exercise_notes is not None:
            if not isinstance(exercise_notes, list):
                errors.append(f"第{index}个动作 notes 必须是数组")
            elif not all(isinstance(note, str) for note in exercise_notes):
                errors.append(f"第{index}个动作 notes 只能包含字符串")

    return errors


def main():
    path = VISUALIZER / "current-workout.js"
    if not path.exists():
        print("[ERROR] current-workout.js 不存在")
        return 1

    try:
        workout = load_workout(path)
    except ValueError as error:
        print(f"[ERROR] {error}")
        return 1

    errors = validate_workout(workout)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print("[OK] Active Workout 有效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
