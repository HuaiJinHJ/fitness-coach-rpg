import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "append_session.py"

VALID_SESSION = {
    "date": "2026-09-12",
    "session_type": "full_body_a",
    "duration_minutes": 45,
    "readiness": {"sleep": "normal", "energy": 7, "pain": []},
    "overall_rpe": 7,
    "notes": "整体状态正常",
    "exercises": [
        {
            "exercise": "seated_chest_press",
            "equipment": "machine",
            "settings": {"seat": 4},
            "status": "completed",
            "sets": [
                {"set_type": "warmup", "weight_kg": 10, "reps": 12},
                {"set_type": "working", "weight_kg": 20, "reps": 12, "rpe": 7},
                {"set_type": "working", "weight_kg": 20, "reps": 11, "rir": 3},
            ],
            "pain": {"location": None, "severity": 0},
            "notes": "胸部发力清楚",
        },
        {
            "exercise": "box_squat",
            "status": "skipped",
            "sets": [],
            "skip_reason": "器械区域拥挤",
            "pain": {"location": None, "severity": 0},
        },
    ],
}


class AppendSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.env = os.environ.copy()
        self.env["FITNESS_COACH_DATA_DIR"] = str(self.data_dir)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        self.temp.cleanup()

    def run_session(self, data):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(data, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=self.env,
            cwd=ROOT,
        )

    def saved(self, date="2026-09-12"):
        path = self.data_dir / "sessions" / f"{date}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_accepts_rpe_rir_warmup_and_skipped_exercise(self):
        result = self.run_session(VALID_SESSION)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = self.saved()
        self.assertEqual(saved["exercises"][0]["sets"][2]["rir"], 3)
        self.assertEqual(saved["exercises"][1]["status"], "skipped")

    def test_converts_pounds_to_kilograms(self):
        data = deepcopy(VALID_SESSION)
        item = data["exercises"][0]["sets"][1]
        item.pop("weight_kg")
        item["weight_lbs"] = 100
        result = self.run_session(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        converted = self.saved()["exercises"][0]["sets"][1]
        self.assertNotIn("weight_lbs", converted)
        self.assertAlmostEqual(converted["weight_kg"], 45.36, places=2)

    def test_same_day_append_preserves_both_exercises_and_updates_supplied_summary(self):
        first = deepcopy(VALID_SESSION)
        first["exercises"] = first["exercises"][:1]
        self.assertEqual(self.run_session(first).returncode, 0)
        second = {
            "date": "2026-09-12",
            "duration_minutes": 50,
            "overall_rpe": 8,
            "readiness": {"sleep": "poor", "energy": 5, "pain": []},
            "notes": "补录下肢动作",
            "exercises": [deepcopy(VALID_SESSION["exercises"][1])],
        }
        self.assertEqual(self.run_session(second).returncode, 0)
        saved = self.saved()
        self.assertEqual(len(saved["exercises"]), 2)
        self.assertEqual(saved["duration_minutes"], 50)
        self.assertEqual(saved["overall_rpe"], 8)
        self.assertEqual(saved["readiness"]["sleep"], "poor")
        self.assertEqual(saved["notes"], "补录下肢动作")

    def assert_rejected_without_file(self, data):
        result = self.run_session(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data_dir / "sessions" / "2026-09-12.json").exists())

    def test_rejects_rpe_above_ten(self):
        data = deepcopy(VALID_SESSION)
        data["exercises"] = [data["exercises"][0]]
        data["exercises"][0]["sets"][1]["rpe"] = 11
        self.assert_rejected_without_file(data)

    def test_rejects_negative_rir(self):
        data = deepcopy(VALID_SESSION)
        data["exercises"] = [data["exercises"][0]]
        data["exercises"][0]["sets"][2]["rir"] = -1
        self.assert_rejected_without_file(data)

    def test_rejects_invalid_date(self):
        data = deepcopy(VALID_SESSION)
        data["exercises"] = [data["exercises"][0]]
        data["date"] = "2026-02-31"
        result = self.run_session(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data_dir / "sessions").exists())

    def test_rejects_completed_exercise_without_working_sets(self):
        data = deepcopy(VALID_SESSION)
        data["exercises"] = [data["exercises"][0]]
        data["exercises"][0]["sets"] = [
            {"set_type": "warmup", "weight_kg": 10, "reps": 12}
        ]
        self.assert_rejected_without_file(data)

    def test_rejects_skipped_exercise_without_reason(self):
        data = deepcopy(VALID_SESSION)
        data["exercises"] = [data["exercises"][1]]
        data["exercises"][0].pop("skip_reason")
        self.assert_rejected_without_file(data)


if __name__ == "__main__":
    unittest.main()
