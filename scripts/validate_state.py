#!/usr/bin/env python3
"""校验 user-data/ 一致性，输出报告，不写文件。

用法：
    python scripts/validate_state.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_json, resolve_user_data

ROOT = Path(__file__).resolve().parent.parent
USER_DATA = resolve_user_data(ROOT)


def main():
    errors, warnings = [], []

    state_file = USER_DATA / "CURRENT-STATE.json"
    if not state_file.exists():
        print("[ERROR] CURRENT-STATE.json 不存在。先运行 init_profile.py。")
        return 1
    try:
        state = load_json(state_file)
    except Exception as e:
        print(f"[ERROR] CURRENT-STATE.json 格式错误: {e}")
        return 1

    sessions_dir = USER_DATA / "sessions"
    if sessions_dir.exists():
        for f in sorted(sessions_dir.glob("*.json")):
            try:
                load_json(f)
            except Exception as e:
                errors.append(f"{f.name} 格式错误: {e}")

    exp = state.get("profile", {}).get("exp", 0)
    if exp < 0:
        errors.append(f"EXP 为负: {exp}")
    level = state.get("profile", {}).get("level", 1)
    if not (1 <= level <= 7):
        warnings.append(f"等级超出范围: {level}")

    attr = state.get("attributes", {})
    for k in ("STR", "CON"):
        v = attr.get(k)
        if v is not None and v < 0:
            warnings.append(f"{k} 为负: {v}")

    story_state = USER_DATA / "story" / "STATE.json"
    if story_state.exists():
        try:
            ss = load_json(story_state)
            ref = ss.get("character_ref", "")
            if "CURRENT-STATE" not in ref:
                warnings.append("story/STATE.json 的 character_ref 未指向 CURRENT-STATE.json")
        except Exception as e:
            errors.append(f"story/STATE.json 格式错误: {e}")

    if not errors and not warnings:
        print("[OK] 一切正常，无错误无警告。")
        return 0
    for e in errors:
        print(f"[ERROR] {e}")
    for w in warnings:
        print(f"[WARN] {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
