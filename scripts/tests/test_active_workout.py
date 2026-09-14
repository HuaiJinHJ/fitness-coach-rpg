import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE_WORKOUT = ROOT / "scripts" / "validate_workout.py"


def render_workout(payload):
    return (
        '(function () {\n'
        '  "use strict";\n'
        '  window.CURRENT_WORKOUT = Object.freeze('
        + json.dumps(payload, ensure_ascii=False)
        + ');\n})();\n'
    )


class ActiveWorkoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.visualizer_dir = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env["FITNESS_COACH_VISUALIZER_DIR"] = str(self.visualizer_dir)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        self.temp.cleanup()

    def run_validator(self):
        return subprocess.run(
            [sys.executable, str(VALIDATE_WORKOUT)],
            cwd=ROOT,
            env=self.env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )

    def write_workout(self, payload):
        (self.visualizer_dir / "current-workout.js").write_text(
            render_workout(payload), encoding="utf-8"
        )

    def valid_payload(self):
        generated_at = datetime.now().astimezone()
        return {
            "schemaVersion": "2.0",
            "initialized": True,
            "sessionId": generated_at.strftime("%Y%m%d-%H%M%S-full-body-a"),
            "generatedAt": generated_at.isoformat(),
            "planLabel": "今天",
            "name": "全身 A",
            "status": "正常执行",
            "notes": ["正常训练无需返回聊天窗口"],
            "exercises": [
                {
                    "order": 1,
                    "name": "坐姿推胸",
                    "prescription": {"sets": 2, "reps": "8-12", "rpe": "6-7"},
                    "notes": ["动作可控"],
                }
            ],
        }

    def test_accepts_session_specific_workout(self):
        self.write_workout(self.valid_payload())
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Active Workout 有效", result.stdout)

    def test_rejects_global_only_prescription(self):
        payload = self.valid_payload()
        payload["prescription"] = {"sets": 2, "reps": "8-12", "rpe": "6-7"}
        payload["exercises"][0].pop("prescription")
        self.write_workout(payload)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("第1个动作 prescription", result.stdout)

    def test_rejects_missing_session_metadata(self):
        for key in ("sessionId", "generatedAt"):
            with self.subTest(key=key):
                payload = self.valid_payload()
                payload.pop(key)
                self.write_workout(payload)
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stdout)

    def test_rejects_workout_generated_on_an_old_date(self):
        payload = self.valid_payload()
        payload["generatedAt"] = "2000-01-01T08:00:00+08:00"
        self.write_workout(payload)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generatedAt 必须是今天", result.stdout)


if __name__ == "__main__":
    unittest.main()
