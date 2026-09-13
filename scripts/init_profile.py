#!/usr/bin/env python3
"""初始化 user-data/，从 assets/starter-profile/ 复制模板。

用法：
    python scripts/init_profile.py --name 小龙
    python scripts/init_profile.py
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_json, atomic_write, resolve_user_data

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "assets" / "starter-profile"
USER_DATA = resolve_user_data(ROOT)
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)
WORKOUT_TEMPLATE = ROOT / "extensions" / "exercise-visualizer" / "current-workout.example.js"


def is_incomplete_profile(path):
    """Return True only for an unfinished scaffold with no workout history."""
    plan_file = path / "CURRENT-PLAN.md"
    state_file = path / "CURRENT-STATE.json"
    if not plan_file.exists() or not state_file.exists():
        return False
    sessions_dir = path / "sessions"
    if sessions_dir.exists() and any(sessions_dir.glob("*.json")):
        return False
    try:
        plan = plan_file.read_text(encoding="utf-8")
        state = load_json(state_file)
    except (OSError, ValueError):
        return False
    has_plan_placeholders = "<待初始化>" in plan or "<初始化后生成" in plan
    has_training_history = bool(state.get("exercise_history")) or bool(
        state.get("next_recommendations")
    )
    return has_plan_placeholders and not has_training_history


def preflight_templates():
    """Read every replacement input before a destructive --force reset."""
    required_files = (
        STARTER / "PROFILE.md",
        STARTER / "CURRENT-PLAN.md",
        STARTER / "CURRENT-STATE.json",
        WORKOUT_TEMPLATE,
    )
    for path in required_files:
        path.read_bytes()
    load_json(STARTER / "CURRENT-STATE.json")


def apply_name(profile_dir, name):
    """Apply an optional name to a prepared or resumed profile."""
    state_file = profile_dir / "CURRENT-STATE.json"
    state = load_json(state_file)
    if name:
        state["profile"]["name"] = name
    atomic_write(state_file, state)

    profile_file = profile_dir / "PROFILE.md"
    text = profile_file.read_text(encoding="utf-8")
    if name:
        text = text.replace("<你的名字>", name)
    profile_file.write_text(text, encoding="utf-8")


def reset_profile(name):
    """Prepare replacements first, then swap them in while preserving rollback data."""
    preflight_templates()
    USER_DATA.parent.mkdir(parents=True, exist_ok=True)
    VISUALIZER.mkdir(parents=True, exist_ok=True)
    workout_file = VISUALIZER / "current-workout.js"
    previous_workout = workout_file.read_bytes() if workout_file.exists() else None

    with tempfile.TemporaryDirectory(prefix=".fitness-init-", dir=USER_DATA.parent) as temp:
        temp_dir = Path(temp)
        staged_profile = temp_dir / "user-data"
        previous_profile = temp_dir / "previous-user-data"
        staged_workout = temp_dir / "current-workout.js"
        shutil.copytree(STARTER, staged_profile, ignore=shutil.ignore_patterns("story"))
        shutil.copy2(WORKOUT_TEMPLATE, staged_workout)
        apply_name(staged_profile, name)

        profile_moved = False
        workout_replaced = False
        try:
            os.replace(staged_workout, workout_file)
            workout_replaced = True
            if USER_DATA.exists():
                os.replace(USER_DATA, previous_profile)
                profile_moved = True
            os.replace(staged_profile, USER_DATA)
        except Exception:
            if profile_moved and not USER_DATA.exists():
                os.replace(previous_profile, USER_DATA)
            if workout_replaced:
                if previous_workout is None:
                    workout_file.unlink(missing_ok=True)
                else:
                    workout_file.write_bytes(previous_workout)
            raise


def main():
    parser = argparse.ArgumentParser(description="初始化训练档案")
    parser.add_argument("--name", help="你的名字")
    parser.add_argument(
        "--force",
        action="store_true",
        help="删除并重建已有训练档案；会永久删除现有记录",
    )
    args = parser.parse_args()

    resume_incomplete = (
        USER_DATA.exists() and not args.force and is_incomplete_profile(USER_DATA)
    )

    if USER_DATA.exists() and not args.force and not resume_incomplete:
        print(f"[ERROR] {USER_DATA} 已存在。用 --force 覆盖（会删除现有数据）。")
        return 1

    if resume_incomplete:
        print(f"[OK] 检测到未完成的空白档案，将继续完善 {USER_DATA}")
        workout_file = VISUALIZER / "current-workout.js"
        if not workout_file.exists():
            VISUALIZER.mkdir(parents=True, exist_ok=True)
            shutil.copy2(WORKOUT_TEMPLATE, workout_file)
        apply_name(USER_DATA, args.name)
    else:
        reset_profile(args.name)

    if not resume_incomplete:
        print(f"[OK] 已初始化 {USER_DATA}")
    print("   空白档案已建立，等待根据个人条件生成训练计划。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
