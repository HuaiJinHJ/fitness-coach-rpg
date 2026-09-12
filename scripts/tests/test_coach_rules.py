import unittest

from scripts.coach_rules import recommend_exercise, session_signature, working_sets


def occurrence(weight=20, reps=(10, 10), rpes=(7, 8), pain=0, date="2026-09-12"):
    sets = [{"set_type": "warmup", "weight_kg": 10, "reps": 12}]
    for rep, rpe in zip(reps, rpes):
        item = {
            "set_type": "working",
            "weight_kg": weight,
            "reps": rep,
        }
        if rpe is not None:
            item["rpe"] = rpe
        sets.append(item)
    return {
        "date": date,
        "status": "completed",
        "equipment": "machine",
        "settings": {"seat": 4},
        "sets": sets,
        "pain": {"location": "knee" if pain else None, "severity": pain},
    }


class CoachRuleTests(unittest.TestCase):
    def test_ignores_warmup_sets(self):
        item = occurrence(weight=20, reps=(10, 9), rpes=(7, 8))
        self.assertEqual(len(working_sets(item)), 2)
        self.assertEqual(session_signature(item), (20, 19))

    def test_increases_after_two_twelves_at_manageable_rpe(self):
        result = recommend_exercise([occurrence(reps=(12, 12), rpes=(7, 8))], 3)
        self.assertEqual(result["action"], "increase_minimum")

    def test_rir_is_used_when_rpe_is_missing(self):
        item = occurrence(reps=(12, 12), rpes=(None, None))
        item["sets"][1]["rir"] = 3
        item["sets"][2]["rir"] = 2
        result = recommend_exercise([item], 3)
        self.assertEqual(result["action"], "increase_minimum")

    def test_holds_weight_in_middle_of_rep_range(self):
        result = recommend_exercise([occurrence(reps=(10, 9), rpes=(7, 8))], 3)
        self.assertEqual(result["action"], "hold_add_reps")

    def test_reduces_after_rpe_nine(self):
        result = recommend_exercise([occurrence(reps=(9, 8), rpes=(8, 9))], 3)
        self.assertEqual(result["action"], "reduce_5_10_percent")

    def test_reduces_after_rir_one(self):
        item = occurrence(reps=(9, 8), rpes=(None, None))
        item["sets"][1]["rir"] = 2
        item["sets"][2]["rir"] = 1
        result = recommend_exercise([item], 3)
        self.assertEqual(result["action"], "reduce_5_10_percent")

    def test_stops_or_substitutes_when_latest_occurrence_has_pain(self):
        result = recommend_exercise([occurrence(pain=3)], 3)
        self.assertEqual(result["action"], "stop_or_substitute")

    def test_applies_ten_percent_reduction_after_ten_days(self):
        result = recommend_exercise([occurrence()], 10)
        self.assertEqual(result["action"], "resume_reduced")
        self.assertEqual(result["load_adjustment_percent"], -10)

    def test_applies_twenty_percent_reduction_after_twenty_days(self):
        result = recommend_exercise([occurrence()], 20)
        self.assertEqual(result["action"], "resume_reduced")
        self.assertEqual(result["load_adjustment_percent"], -20)

    def test_rebuilds_baseline_after_thirty_days(self):
        result = recommend_exercise([occurrence()], 35)
        self.assertEqual(result["action"], "rebuild_baseline")
        self.assertIsNone(result["load_adjustment_percent"])

    def test_reviews_three_stagnant_occurrences(self):
        history = [
            occurrence(date="2026-09-01"),
            occurrence(date="2026-09-05"),
            occurrence(date="2026-09-09"),
        ]
        result = recommend_exercise(history, 3)
        self.assertEqual(result["action"], "review_stagnation")

    def test_deloads_after_two_consecutive_load_declines_over_ten_percent(self):
        history = [
            occurrence(weight=30, date="2026-09-01"),
            occurrence(weight=26, date="2026-09-05"),
            occurrence(weight=22, date="2026-09-09"),
        ]
        result = recommend_exercise(history, 3)
        self.assertEqual(result["action"], "deload")


if __name__ == "__main__":
    unittest.main()
