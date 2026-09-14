#!/usr/bin/env python3
"""Validate that conversational onboarding produced the long-term profile and plan."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import resolve_user_data

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = resolve_user_data(ROOT)

REQUIRED_PROFILE_FIELDS = (
    "目标",
    "训练水平",
    "设备",
    "现实频率",
    "可用时长",
    "伤病或动作限制",
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


def main():
    errors = []
    validate_profile(errors)
    validate_plan(errors)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] 个性化初始化内容完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
