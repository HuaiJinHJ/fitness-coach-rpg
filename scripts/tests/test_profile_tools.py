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


class ProfileToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.env = os.environ.copy()
        self.env["FITNESS_COACH_DATA_DIR"] = str(self.data_dir)
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

    def test_initializes_blank_personalized_profile(self):
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
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
