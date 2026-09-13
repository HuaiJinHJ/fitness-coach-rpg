import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "scripts" / "init_profile.py"
VALIDATE = ROOT / "scripts" / "validate_state.py"
VALIDATE_ONBOARDING = ROOT / "scripts" / "validate_onboarding.py"
VISUALIZER_INDEX = ROOT / "extensions" / "exercise-visualizer" / "index.html"
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"


class ProfileToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.visualizer_dir = Path(self.temp.name) / "visualizer"
        self.env = os.environ.copy()
        self.env["FITNESS_COACH_DATA_DIR"] = str(self.data_dir)
        self.env["FITNESS_COACH_VISUALIZER_DIR"] = str(self.visualizer_dir)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, script, *args):
        return subprocess.run(
            [sys.executable, str(script), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=self.env,
            cwd=ROOT,
        )

    def initialize(self):
        return self.run_tool(INIT, "--name", "怀瑾")

    def write_completed_onboarding(self):
        if not self.data_dir.exists():
            result = self.initialize()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.data_dir / "PROFILE.md").write_text(
            """# 个人档案 PROFILE

- **姓名**：`测试用户`
- **基础数据**：`未提供`
- **目标**：`提升基础力量`
- **训练水平**：`新手`
- **设备**：`商业健身房`
- **现实频率**：`每周 2 次`
- **可用时长**：`每次 45 分钟`
- **教练模式**：纯教练模式
- **伤病或动作限制**：`无`
""",
            encoding="utf-8",
        )
        (self.data_dir / "CURRENT-PLAN.md").write_text(
            """# 当前计划 CURRENT-PLAN

## 计划依据

- 目标：提升基础力量
- 每周频率：2 次

## 当前阶段

- 建立动作基线

## 动作安排

训练日一：器械推胸，2 组，每组 8-12 次，RPE 6-7。

## 调整与安全边界

保持无痛和动作可控。
""",
            encoding="utf-8",
        )
        self.visualizer_dir.mkdir(parents=True, exist_ok=True)
        (self.visualizer_dir / "current-workout.js").write_text(
            """(function () {
  window.CURRENT_WORKOUT = Object.freeze({
    "schemaVersion": "1.0",
    "initialized": true,
    "planLabel": "下一次",
    "name": "训练日一",
    "status": "可以开始",
    "prescription": { "sets": 2, "reps": "8-12", "rpe": "6-7" },
    "notes": ["保持动作可控"],
    "exercises": [{ "name": "器械推胸", "order": 1 }]
  });
})();
""",
            encoding="utf-8",
        )

    def test_initializes_blank_personalized_profile(self):
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("等待根据个人条件生成训练计划", result.stdout)
        self.assertNotIn("直接开始训练", result.stdout)
        state = json.loads((self.data_dir / "CURRENT-STATE.json").read_text(encoding="utf-8"))
        profile = (self.data_dir / "PROFILE.md").read_text(encoding="utf-8")
        plan = (self.data_dir / "CURRENT-PLAN.md").read_text(encoding="utf-8")
        self.assertEqual(state["profile"], {"name": "怀瑾", "mode": "pure_coach"})
        self.assertNotIn("RPG", profile)
        self.assertNotIn("教练体系", profile)
        for personalized_default in (
            "全身 A",
            "全身 B",
            "坐姿推胸",
            "坐姿划船",
            "罗马尼亚硬拉",
            "腿举",
        ):
            self.assertNotIn(personalized_default, plan)
        self.assertIn("训练目标", plan)
        self.assertIn("每周频率", plan)
        self.assertIn("动作安排", plan)
        self.assertFalse((self.data_dir / "story").exists())

    def test_theme_argument_is_not_available(self):
        result = self.run_tool(INIT, "--theme", "武侠")
        self.assertNotEqual(result.returncode, 0)

    def test_initialization_creates_untracked_blank_workout_card(self):
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        card_path = self.visualizer_dir / "current-workout.js"
        self.assertTrue(card_path.exists(), "初始化应生成本地 GIF 训练卡")
        card = card_path.read_text(encoding="utf-8")
        self.assertIn('"initialized": false', card)
        self.assertNotIn("坐姿推胸", card)

    def test_incomplete_profile_can_resume_without_overwriting_partial_answers(self):
        self.assertEqual(self.initialize().returncode, 0)
        profile_path = self.data_dir / "PROFILE.md"
        profile_path.write_text("我的现有档案", encoding="utf-8")
        second = self.run_tool(INIT, "--name", "其他人")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("继续完善", second.stdout)
        self.assertEqual(profile_path.read_text(encoding="utf-8"), "我的现有档案")

    def test_completed_profile_is_not_overwritten(self):
        self.assertEqual(self.initialize().returncode, 0)
        plan_path = self.data_dir / "CURRENT-PLAN.md"
        plan_path.write_text("# 当前计划\n\n## 动作安排\n\n按个人条件生成。", encoding="utf-8")
        second = self.run_tool(INIT, "--name", "其他人")
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(plan_path.read_text(encoding="utf-8"), "# 当前计划\n\n## 动作安排\n\n按个人条件生成。")

    def test_profile_with_session_is_not_treated_as_incomplete(self):
        self.assertEqual(self.initialize().returncode, 0)
        sessions = self.data_dir / "sessions"
        sessions.mkdir()
        (sessions / "2026-09-13.json").write_text("{}", encoding="utf-8")
        second = self.run_tool(INIT)
        self.assertNotEqual(second.returncode, 0)

    def test_force_resets_incomplete_profile(self):
        self.assertEqual(self.initialize().returncode, 0)
        profile_path = self.data_dir / "PROFILE.md"
        profile_path.write_text("不应保留的残缺档案", encoding="utf-8")
        result = self.run_tool(INIT, "--force", "--name", "新用户")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        profile = profile_path.read_text(encoding="utf-8")
        self.assertNotIn("不应保留的残缺档案", profile)
        self.assertIn("新用户", profile)

    def test_force_keeps_existing_profile_when_destination_is_unwritable(self):
        self.assertEqual(self.initialize().returncode, 0)
        profile_path = self.data_dir / "PROFILE.md"
        profile_path.write_text("必须保留的现有档案", encoding="utf-8")
        (self.visualizer_dir / "current-workout.js").unlink()
        self.visualizer_dir.rmdir()
        self.visualizer_dir.write_text("阻止创建目录", encoding="utf-8")

        result = self.run_tool(INIT, "--force", "--name", "新用户")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(profile_path.read_text(encoding="utf-8"), "必须保留的现有档案")

    def test_visualizer_prompts_when_personal_workout_is_not_initialized(self):
        page = VISUALIZER_INDEX.read_text(encoding="utf-8")
        self.assertIn("workout.initialized === false", page)
        self.assertIn("请先在项目中对 AI 说“初始化健身教练”", page)

    def test_skill_marks_generated_workout_card_as_initialized(self):
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn('`"initialized": true`', skill)
        self.assertIn("`prescription`", skill)
        self.assertIn("`exercises`", skill)
        self.assertIn("合法 JSON", skill)
        self.assertIn("python scripts/validate_onboarding.py", skill)

    def test_readme_does_not_present_personal_plan_as_default(self):
        readme = README.read_text(encoding="utf-8")
        self.assertNotIn("每周完成一次即为成功，完成两次更理想", readme)
        self.assertNotIn("教练：今天进行全身 A", readme)
        self.assertIn("具体频率和训练结构由初始化结果决定", readme)

    def test_onboarding_validator_accepts_completed_personalization(self):
        self.write_completed_onboarding()
        result = self.run_tool(VALIDATE_ONBOARDING)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("初始化内容完整", result.stdout)

    def test_onboarding_validator_rejects_each_incomplete_artifact(self):
        cases = (
            "profile_placeholders",
            "profile_empty_values",
            "plan_placeholders",
            "plan_empty_sections",
            "workout_missing",
            "workout_not_initialized",
            "workout_malformed",
        )
        for case in cases:
            with self.subTest(case=case):
                self.write_completed_onboarding()
                if case == "profile_placeholders":
                    (self.data_dir / "PROFILE.md").write_text(
                        (ROOT / "assets" / "starter-profile" / "PROFILE.md").read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                    expected = "PROFILE.md"
                elif case == "profile_empty_values":
                    (self.data_dir / "PROFILE.md").write_text(
                        """# 个人档案 PROFILE

- **目标**：``
- **训练水平**：``
- **设备**：``
- **现实频率**：``
- **可用时长**：``
- **伤病或动作限制**：``
""",
                        encoding="utf-8",
                    )
                    expected = "PROFILE.md"
                elif case == "plan_placeholders":
                    (self.data_dir / "CURRENT-PLAN.md").write_text(
                        (ROOT / "assets" / "starter-profile" / "CURRENT-PLAN.md").read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                    expected = "CURRENT-PLAN.md"
                elif case == "plan_empty_sections":
                    (self.data_dir / "CURRENT-PLAN.md").write_text(
                        """# 当前计划 CURRENT-PLAN

## 计划依据

## 当前阶段

## 动作安排

## 调整与安全边界
""",
                        encoding="utf-8",
                    )
                    expected = "CURRENT-PLAN.md"
                elif case == "workout_missing":
                    (self.visualizer_dir / "current-workout.js").unlink()
                    expected = "current-workout.js"
                elif case == "workout_not_initialized":
                    workout = self.visualizer_dir / "current-workout.js"
                    workout.write_text(
                        workout.read_text(encoding="utf-8").replace(
                            '"initialized": true', '"initialized": false'
                        ),
                        encoding="utf-8",
                    )
                    expected = "initialized: true"
                elif case == "workout_malformed":
                    (self.visualizer_dir / "current-workout.js").write_text(
                        "window.CURRENT_WORKOUT = Object.freeze({initialized: true, exercises: [{name:}]});",
                        encoding="utf-8",
                    )
                    expected = "JSON"
                result = self.run_tool(VALIDATE_ONBOARDING)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)

    def test_validate_accepts_complete_pure_coach_state_and_ignores_story(self):
        self.assertEqual(self.initialize().returncode, 0)
        story = self.data_dir / "story"
        story.mkdir(exist_ok=True)
        (story / "STATE.json").write_text("not json", encoding="utf-8")
        result = self.run_tool(VALIDATE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validate_rejects_each_missing_required_state_key(self):
        self.assertEqual(self.initialize().returncode, 0)
        state_path = self.data_dir / "CURRENT-STATE.json"
        original = json.loads(state_path.read_text(encoding="utf-8"))
        for key in ("recovery", "exercise_history", "next_recommendations"):
            with self.subTest(key=key):
                state = dict(original)
                state.pop(key)
                state_path.write_text(json.dumps(state), encoding="utf-8")
                result = self.run_tool(VALIDATE)
                self.assertNotEqual(result.returncode, 0)

    def test_validate_rejects_invalid_session_effort_and_pain(self):
        self.assertEqual(self.initialize().returncode, 0)
        sessions = self.data_dir / "sessions"
        sessions.mkdir(exist_ok=True)
        bad_session = {
            "schema_version": "2.0",
            "date": "2026-02-31",
            "exercises": [{
                "exercise": "leg_press",
                "status": "completed",
                "sets": [{"weight_kg": 30, "reps": 10, "rpe": 12, "rir": -1}],
                "pain": {"location": "knee", "severity": 11},
            }],
        }
        (sessions / "bad.json").write_text(json.dumps(bad_session), encoding="utf-8")
        result = self.run_tool(VALIDATE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("日期", result.stdout)
        self.assertIn("rpe", result.stdout)
        self.assertIn("rir", result.stdout)
        self.assertIn("疼痛", result.stdout)


if __name__ == "__main__":
    unittest.main()
