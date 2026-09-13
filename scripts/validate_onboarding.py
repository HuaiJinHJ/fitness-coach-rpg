#!/usr/bin/env python3
"""Validate that conversational onboarding produced every required artifact."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import resolve_user_data

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = resolve_user_data(ROOT)
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)

REQUIRED_PROFILE_FIELDS = (
    "目标",
    "训练水平",
    "设备",
    "现实频率",
    "可用时长",
    "伤病或动作限制",
)
REQUIRED_WORKOUT_KEYS = (
    "planLabel",
    "name",
    "status",
    "prescription",
    "notes",
    "exercises",
)


def field_value(text, label):
    pattern = rf"^\s*-\s*\*\*{re.escape(label)}\*\*\s*[：:]\s*`?([^`\n]*)`?\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def validate_profile(errors):
    path = USER_DATA / "PROFILE.md"
    if not path.exists():
        errors.append("PROFILE.md 不存在")
        return
    text = path.read_text(encoding="utf-8")
    for label in REQUIRED_PROFILE_FIELDS:
        value = field_value(text, label)
        if not value or re.search(r"<[^>]+>", value):
            errors.append(f"PROFILE.md 的{label}尚未完成")


def validate_plan(errors):
    path = USER_DATA / "CURRENT-PLAN.md"
    if not path.exists():
        errors.append("CURRENT-PLAN.md 不存在")
        return
    text = path.read_text(encoding="utf-8")
    if re.search(r"<[^>]+>", text):
        errors.append("CURRENT-PLAN.md 仍包含初始化占位符")
    for heading in ("计划依据", "当前阶段", "动作安排", "调整与安全边界"):
        section = re.search(
            rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if section is None:
            errors.append(f"CURRENT-PLAN.md 缺少{heading}")
        elif not re.search(r"[\w\u4e00-\u9fff]", section.group(1)):
            errors.append(f"CURRENT-PLAN.md 的{heading}没有内容")


def validate_workout(errors):
    path = VISUALIZER / "current-workout.js"
    if not path.exists():
        errors.append("current-workout.js 不存在")
        return
    text = path.read_text(encoding="utf-8")
    match = re.search(r"Object\.freeze\(\s*(\{.*\})\s*\)\s*;", text, re.DOTALL)
    if match is None:
        errors.append("current-workout.js 必须使用 current-workout.example.js 的 JSON 格式")
        return
    try:
        workout = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        errors.append(f"current-workout.js 的 JSON 格式错误: {error.msg}")
        return
    if workout.get("initialized") is not True:
        errors.append("current-workout.js 必须设置 initialized: true")
    for key in REQUIRED_WORKOUT_KEYS:
        if key not in workout:
            errors.append(f"current-workout.js 缺少 {key}")
    for key in ("planLabel", "name", "status"):
        if not isinstance(workout.get(key), str) or not workout[key].strip():
            errors.append(f"current-workout.js 的 {key} 不能为空")
    prescription = workout.get("prescription")
    if not isinstance(prescription, dict):
        errors.append("current-workout.js 的 prescription 格式错误")
    else:
        sets = prescription.get("sets")
        if not isinstance(sets, (int, float)) or isinstance(sets, bool) or sets <= 0:
            errors.append("current-workout.js 的 prescription.sets 必须大于 0")
        for key in ("reps", "rpe"):
            if not isinstance(prescription.get(key), str) or not prescription[key].strip():
                errors.append(f"current-workout.js 的 prescription.{key} 不能为空")
    if not isinstance(workout.get("notes"), list):
        errors.append("current-workout.js 的 notes 必须是数组")
    exercises = workout.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        errors.append("current-workout.js 的 exercises 必须至少包含一个动作")
    else:
        for index, exercise in enumerate(exercises, start=1):
            if not isinstance(exercise, dict):
                errors.append(f"current-workout.js 第{index}个动作格式错误")
                continue
            if not isinstance(exercise.get("name"), str) or not exercise["name"].strip():
                errors.append(f"current-workout.js 第{index}个动作名称不能为空")
            order = exercise.get("order")
            if not isinstance(order, int) or isinstance(order, bool) or order <= 0:
                errors.append(f"current-workout.js 第{index}个动作 order 必须为正整数")


def main():
    errors = []
    validate_profile(errors)
    validate_plan(errors)
    validate_workout(errors)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] 个性化初始化内容完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
