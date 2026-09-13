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


def main():
    parser = argparse.ArgumentParser(description="初始化训练档案")
    parser.add_argument("--name", help="你的名字")
    parser.add_argument(
        "--force",
        action="store_true",
        help="删除并重建已有训练档案；会永久删除现有记录",
    )
    args = parser.parse_args()

    if USER_DATA.exists() and not args.force:
        print(f"[ERROR] {USER_DATA} 已存在。用 --force 覆盖（会删除现有数据）。")
        return 1

    if USER_DATA.exists():
        shutil.rmtree(USER_DATA)
    shutil.copytree(STARTER, USER_DATA, ignore=shutil.ignore_patterns("story"))
    VISUALIZER.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKOUT_TEMPLATE, VISUALIZER / "current-workout.js")

    # 填初始值
    state_file = USER_DATA / "CURRENT-STATE.json"
    state = load_json(state_file)
    if args.name:
        state["profile"]["name"] = args.name
    atomic_write(state_file, state)

    # 同步 PROFILE.md 占位符
    profile_file = USER_DATA / "PROFILE.md"
    text = profile_file.read_text(encoding="utf-8")
    if args.name:
        text = text.replace("<你的名字>", args.name)
    profile_file.write_text(text, encoding="utf-8")

    print(f"[OK] 已初始化 {USER_DATA}")
    print("   空白档案已建立，等待根据个人条件生成训练计划。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
