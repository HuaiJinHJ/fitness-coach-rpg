#!/usr/bin/env python3
"""Validate that conversational onboarding produced every required artifact."""
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


def field_line(text, label):
    marker = f"**{label}**"
    return next((line for line in text.splitlines() if marker in line), None)


def validate_profile(errors):
    path = USER_DATA / "PROFILE.md"
    if not path.exists():
        errors.append("PROFILE.md 不存在")
        return
    text = path.read_text(encoding="utf-8")
    for label in REQUIRED_PROFILE_FIELDS:
        line = field_line(text, label)
        if line is None or re.search(r"<[^>]+>", line):
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
        if heading not in text:
            errors.append(f"CURRENT-PLAN.md 缺少{heading}")


def validate_workout(errors):
    path = VISUALIZER / "current-workout.js"
    if not path.exists():
        errors.append("current-workout.js 不存在")
        return
    text = path.read_text(encoding="utf-8")
    if not re.search(r"\binitialized\s*:\s*true\b", text):
        errors.append("current-workout.js 必须设置 initialized: true")
    for key in REQUIRED_WORKOUT_KEYS:
        if not re.search(rf"\b{re.escape(key)}\s*:", text):
            errors.append(f"current-workout.js 缺少 {key}")
    exercises = re.search(r"\bexercises\s*:\s*\[(.*?)\]", text, re.DOTALL)
    if exercises is None or not re.search(r"\bname\s*:", exercises.group(1)):
        errors.append("current-workout.js 的 exercises 必须至少包含一个动作")


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
