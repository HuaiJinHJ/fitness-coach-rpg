import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "update_summary.py"


def exercise(name, weight, reps=(12, 12), rpe=7, pain=0):
    return {
        "exercise": name,
        "equipment": "machine",
        "settings": {"seat": 4},
        "status": "completed",
        "sets": [
            {"set_type": "working", "weight_kg": weight, "reps": reps[0], "rpe": rpe},
            {"set_type": "working", "weight_kg": weight, "reps": reps[1], "rpe": rpe},
        ],
        "pain": {"location": "knee" if pain else None, "severity": pain},
    }


class UpdateSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        (self.data_dir / "sessions").mkdir(parents=True)
        self.env = os.environ.copy()
        self.env["FITNESS_COACH_DATA_DIR"] = str(self.data_dir)
        self.env["PYTHONIOENCODING"] = "utf-8"
        old_state = {
            "schema_version": "1.0",
            "profile": {"name": "怀瑾", "theme": "剑与魔法", "level": 3, "exp": 600},
            "attributes": {"STR": 10},
            "recent_bests": {},
        }
        self.write_json(self.data_dir / "CURRENT-STATE.json", old_state)

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def write_session(self, date, exercises, overall_rpe=7):
        self.write_json(
            self.data_dir / "sessions" / f"{date}.json",
            {
                "schema_version": "2.0",
                "date": date,
                "session_type": "full_body_a",
                "overall_rpe": overall_rpe,
                "exercises": exercises,
            },
        )

    def run_summary(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=self.env,
            cwd=ROOT,
        )

    def test_replaces_rpg_fields_with_coaching_state_and_reasons(self):
        today = datetime.now().date()
        first = (today - timedelta(days=4)).isoformat()
        latest = today.isoformat()
        self.write_session(first, [exercise("seated_chest_press", 20, pain=2)])
        self.write_session(latest, [
            exercise("seated_chest_press", 20),
            exercise("leg_press", 30, pain=3),
        ], overall_rpe=8)

        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.data_dir / "CURRENT-STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], "2.0")
        self.assertEqual(state["profile"], {"name": "怀瑾", "mode": "pure_coach"})
        self.assertEqual(state["recovery"]["last_session_date"], latest)
        self.assertEqual(state["recovery"]["days_since_last"], 0)
        self.assertIn("seated_chest_press", state["exercise_history"])
        self.assertIn("seated_chest_press", state["next_recommendations"])
        self.assertIn("reason", state["next_recommendations"]["seated_chest_press"])
        self.assertEqual(
            state["recovery"]["active_pain"],
            [{"exercise": "leg_press", "location": "knee", "severity": 3, "date": latest}],
        )
        self.assertNotIn("exp", state["profile"])
        self.assertNotIn("attributes", state)
        self.assertNotIn("recent_bests", state)

    def test_keeps_only_three_latest_completed_occurrences(self):
        today = datetime.now().date()
        for offset in (9, 6, 3, 0):
            date = (today - timedelta(days=offset)).isoformat()
            self.write_session(date, [exercise("seated_row", 20 + offset)])
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.data_dir / "CURRENT-STATE.json").read_text(encoding="utf-8"))
        history = state["exercise_history"]["seated_row"]
        self.assertEqual(len(history), 3)
        self.assertEqual(history[-1]["date"], today.isoformat())

    def test_skipped_exercise_does_not_create_performance_history(self):
        today = datetime.now().date().isoformat()
        self.write_session(today, [{
            "exercise": "box_squat",
            "status": "skipped",
            "sets": [],
            "skip_reason": "器械区域拥挤",
            "pain": {"location": None, "severity": 0},
        }])
        result = self.run_summary()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.data_dir / "CURRENT-STATE.json").read_text(encoding="utf-8"))
        self.assertNotIn("box_squat", state["exercise_history"])


if __name__ == "__main__":
    unittest.main()
