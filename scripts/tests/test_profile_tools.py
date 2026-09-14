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
        self.assertTrue(card_path.exists(), "初始化应生成本地空白训练卡")
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

    def test_visualizer_prompts_to_generate_active_workout(self):
        page = VISUALIZER_INDEX.read_text(encoding="utf-8")
        self.assertIn("workout.initialized === false", page)
        self.assertIn("回到项目对话输入“开始训练”", page)
        self.assertIn("请先生成本次训练", page)

    def test_skill_defines_active_workout_lifecycle(self):
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("Active Workout", skill)
        self.assertIn('schemaVersion: "2.0"', skill)
        self.assertIn("独立 `prescription`", skill)
        self.assertIn("python scripts/validate_workout.py", skill)
        self.assertIn("python scripts/open_workout.py", skill)
        self.assertIn("python scripts/validate_workout.py --session-id <本次 sessionId>", skill)
        self.assertIn("python scripts/open_workout.py --session-id <本次 sessionId>", skill)
        self.assertIn("聊天不重复输出完整训练处方", skill)

    def test_skill_does_not_force_fixed_preworkout_questionnaire(self):
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("默认不固定询问睡眠、精神状态和疼痛", skill)
        self.assertIn("用户已主动提供的信息不得重复追问", skill)

    def test_visualizer_renders_per_exercise_prescription(self):
        page = VISUALIZER_INDEX.read_text(encoding="utf-8")
        self.assertIn("exercise.prescription", page)
        self.assertIn('addMetric(metrics, "正式组", exercise.prescription.sets)', page)
        self.assertIn('addMetric(metrics, "次数", exercise.prescription.reps)', page)
        self.assertIn('addMetric(metrics, "目标 RPE", exercise.prescription.rpe)', page)
        self.assertNotIn("workout.prescription.sets", page)

    def test_visualizer_identifies_active_session(self):
        page = VISUALIZER_INDEX.read_text(encoding="utf-8")
        self.assertIn("workout.sessionId", page)
        self.assertIn("workout.status", page)

    def test_readme_does_not_present_personal_plan_as_default(self):
        readme = README.read_text(encoding="utf-8")
        self.assertNotIn("每周完成一次即为成功，完成两次更理想", readme)
        self.assertNotIn("教练：今天进行全身 A", readme)
        self.assertIn("具体频率和训练结构由初始化结果决定", readme)

    def test_readme_explains_planning_and_training_conversations(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("规划对话", readme)
        self.assertIn("训练对话", readme)
        self.assertIn("开始训练", readme)
        self.assertIn("默认浏览器", readme)

    def test_onboarding_validator_accepts_completed_personalization(self):
        self.write_completed_onboarding()
        result = self.run_tool(VALIDATE_ONBOARDING)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("初始化内容完整", result.stdout)

    def test_onboarding_validator_accepts_existing_semantic_labels(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "PROFILE.md").write_text(
            """# 个人档案 PROFILE

- **目标**：塑形 / 体态重组
- **训练水平**：器械训练新手
- **设备**：商业健身房全器械
- **现实频率**：每周稳定 `1-2` 次；早晨可支配 `40-60` 分钟
- **伤病史**：膝盖目前无痛；训练中以无痛和动作可控为边界
""",
            encoding="utf-8",
        )
        (self.data_dir / "CURRENT-PLAN.md").write_text(
            """# 本周计划 CURRENT-PLAN

## 本阶段安排

每周完成 1-2 次，每次 40-60 分钟。

| 顺序 | 类型 | 内容 |
|:---|:---|:---|
| 下一次 | 全身 A | 每项 2 组，8-12 次，RPE 6-7 |

## 本阶段重点

- 出现疼痛就停止对应动作并记录。
""",
            encoding="utf-8",
        )
        result = self.run_tool(VALIDATE_ONBOARDING)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_onboarding_validator_rejects_each_incomplete_artifact(self):
        cases = (
            "profile_placeholders",
            "profile_empty_values",
            "plan_placeholders",
            "plan_empty_sections",
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
