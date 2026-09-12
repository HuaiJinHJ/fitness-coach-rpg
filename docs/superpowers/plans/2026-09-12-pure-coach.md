# Pure Coach Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the local Fitness Coach RPG save into a reliable pure coaching workflow with isolated tests, lightweight workout logging, recovery-aware recommendations, and no RPG or named-coach behavior.

**Architecture:** Keep Markdown as the human-readable profile and plan, JSON sessions as append-only training facts, and `CURRENT-STATE.json` as a derived snapshot. Put deterministic load and recovery decisions in a small pure-Python rules module; the AI reads those facts and explains the recommendation without inventing missing data.

**Tech Stack:** Python 3.8+ standard library, JSON, Markdown, `unittest`, Git.

---

## File map

- Create `scripts/coach_rules.py`: pure functions for working-set extraction, double progression, interruption adjustments, stagnation, and decline detection.
- Create `scripts/tests/test_data_isolation.py`: prove tests use a temporary data directory.
- Create `scripts/tests/test_append_session.py`: validate RPE/RIR, skipped exercises, dates, and same-day append behavior.
- Create `scripts/tests/test_coach_rules.py`: verify progression, fatigue, pain, interruption, stagnation, and decline decisions.
- Create `scripts/tests/test_update_summary.py`: verify the derived state schema and reasons.
- Modify `scripts/_common.py`: resolve the runtime data directory from an optional environment override.
- Modify `scripts/append_session.py`: use the resolved data directory and accept the pure-coach session schema.
- Modify `scripts/update_summary.py`: replace EXP and attributes with training history and next recommendations.
- Modify `scripts/validate_state.py`: validate pure-coach state and sessions without inspecting story data.
- Modify `scripts/init_profile.py`: remove RPG arguments and initialize a pure-coach profile.
- Modify `scripts/test_regression.py`: stop deleting real `user-data`; run the isolated test suite with portable text output.
- Modify `assets/starter-profile/PROFILE.md`: replace named-coach and RPG fields with coaching principles.
- Modify `assets/starter-profile/CURRENT-PLAN.md`: use sequential full-body A/B.
- Modify `assets/starter-profile/CURRENT-STATE.json`: use the pure-coach derived-state schema.
- Modify `assets/starter-profile/example-session.json`: demonstrate working sets, RPE/RIR, equipment, skipped status, pain, and notes.
- Modify `SKILL.md`: make pure coaching the only active behavior in this save.
- Modify `README.md`: explain the simplified local workflow and remove claims that scripts do not implement.
- Modify `examples/MINIMAL-RUN.md`: show plan-first, adjust-on-exception usage.
- Modify `references/test-scenarios.md`: align manual scenarios with pure coaching.
- Modify `CHANGELOG.md`: record the pure-coach conversion.
- Update ignored runtime files `user-data/PROFILE.md`, `user-data/CURRENT-PLAN.md`, and `user-data/CURRENT-STATE.json`: preserve the user's confirmed profile and activate the new schema.

### Task 1: Isolate every test from real training data

**Files:**
- Modify: `scripts/_common.py`
- Modify: `scripts/append_session.py`
- Modify: `scripts/update_summary.py`
- Modify: `scripts/validate_state.py`
- Modify: `scripts/init_profile.py`
- Create: `scripts/tests/test_data_isolation.py`
- Modify: `scripts/test_regression.py`

- [ ] **Step 1: Write the failing isolation test**

Create `scripts/tests/test_data_isolation.py`:

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts._common import resolve_user_data


class DataIsolationTests(unittest.TestCase):
    def test_default_is_repository_user_data(self):
        root = Path("C:/repo")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_user_data(root), root / "user-data")

    def test_environment_override_uses_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"FITNESS_COACH_DATA_DIR": temp_dir}):
                self.assertEqual(resolve_user_data(Path("C:/repo")), Path(temp_dir).resolve())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the isolation test and verify it fails**

Run: `python -m unittest scripts.tests.test_data_isolation -v`

Expected: `ImportError` because `resolve_user_data` does not exist.

- [ ] **Step 3: Add one data-directory resolver**

Add to `scripts/_common.py`:

```python
def resolve_user_data(root):
    override = os.environ.get("FITNESS_COACH_DATA_DIR")
    if override:
        return Path(override).resolve()
    return Path(root) / "user-data"
```

Replace each hard-coded `ROOT / "user-data"` in `append_session.py`, `update_summary.py`, `validate_state.py`, and `init_profile.py` with:

```python
from _common import load_json, atomic_write, resolve_user_data

USER_DATA = resolve_user_data(ROOT)
```

- [ ] **Step 4: Replace the destructive regression runner**

Replace `scripts/test_regression.py` with:

```python
#!/usr/bin/env python3
"""Run the isolated standard-library test suite."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "scripts" / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
```

Use ASCII-only status text in Python scripts (`[OK]`, `[ERROR]`, `[WARN]`) so Windows console encoding cannot stop a test or data update.

- [ ] **Step 5: Run the isolation test**

Run: `python -m unittest scripts.tests.test_data_isolation -v`

Expected: two tests pass. Confirm `git status --short -- user-data` produces no test-created files.

- [ ] **Step 6: Commit the isolation fix**

```bash
git add scripts/_common.py scripts/append_session.py scripts/update_summary.py scripts/validate_state.py scripts/init_profile.py scripts/test_regression.py scripts/tests/test_data_isolation.py
git commit -m "fix: isolate tests from personal training data"
```

### Task 2: Define and validate the lightweight session format

**Files:**
- Modify: `scripts/append_session.py`
- Create: `scripts/tests/test_append_session.py`
- Modify: `assets/starter-profile/example-session.json`

- [ ] **Step 1: Write failing session-validation tests**

Create `scripts/tests/test_append_session.py` with temporary directories and subprocess environment overrides. The core cases must be expressed exactly as follows:

```python
VALID_SESSION = {
    "date": "2026-09-12",
    "session_type": "full_body_a",
    "duration_minutes": 45,
    "readiness": {"sleep": "normal", "energy": 7, "pain": []},
    "overall_rpe": 7,
    "exercises": [
        {
            "exercise": "seated_chest_press",
            "equipment": "machine",
            "settings": {"seat": 4},
            "status": "completed",
            "sets": [
                {"set_type": "warmup", "weight_kg": 10, "reps": 12},
                {"set_type": "working", "weight_kg": 20, "reps": 12, "rpe": 7},
                {"set_type": "working", "weight_kg": 20, "reps": 11, "rir": 3}
            ],
            "pain": {"location": None, "severity": 0},
            "notes": "胸部发力清楚"
        },
        {
            "exercise": "box_squat",
            "status": "skipped",
            "sets": [],
            "skip_reason": "器械区域拥挤",
            "pain": {"location": None, "severity": 0}
        }
    ]
}
```

Tests must assert:

```python
self.assertEqual(result.returncode, 0)
self.assertEqual(saved["exercises"][0]["sets"][2]["rir"], 3)
self.assertEqual(saved["exercises"][1]["status"], "skipped")
self.assertNotIn("weight_lbs", converted_set)
self.assertAlmostEqual(converted_set["weight_kg"], 45.36, places=2)
```

Add failing cases for `rpe=11`, `rir=-1`, an invalid date, and a completed exercise with no working sets. Each must return non-zero and leave the target session file absent.

- [ ] **Step 2: Run the append tests and verify failures**

Run: `python -m unittest scripts.tests.test_append_session -v`

Expected: failures for RIR, skipped exercises, date validation, or environment isolation behavior not yet implemented.

- [ ] **Step 3: Implement minimal validation and same-day merging**

In `scripts/append_session.py`:

```python
def validate_date(value):
    datetime.strptime(value, "%Y-%m-%d")


def validate_exercise(exercise):
    status = exercise.get("status", "completed")
    sets = exercise.get("sets", [])
    if status == "skipped":
        if not exercise.get("skip_reason"):
            raise ValueError(f"动作 {exercise.get('exercise', '?')} 缺少 skip_reason")
        return
    working_sets = [item for item in sets if item.get("set_type", "working") == "working"]
    if not working_sets:
        raise ValueError(f"动作 {exercise.get('exercise', '?')} 没有正式组")
    for index, item in enumerate(sets, start=1):
        weight = item.get("weight_kg")
        reps = item.get("reps")
        rpe = item.get("rpe")
        rir = item.get("rir")
        if weight is not None and weight < 0:
            raise ValueError(f"第{index}组 weight_kg 不能小于 0")
        if reps is not None and reps <= 0:
            raise ValueError(f"第{index}组 reps 必须大于 0")
        if rpe is not None and not 1 <= rpe <= 10:
            raise ValueError(f"第{index}组 rpe 必须为 1-10")
        if rir is not None and not 0 <= rir <= 10:
            raise ValueError(f"第{index}组 rir 必须为 0-10")
```

Validate the date before creating directories. When appending to an existing day, extend `exercises` and update only session-level fields explicitly provided by the new input: `duration_minutes`, `overall_rpe`, `readiness`, and `notes`.

- [ ] **Step 4: Update the example session**

Replace `assets/starter-profile/example-session.json` with `VALID_SESSION`, encoded as valid JSON. The example must use a warm-up set, two working sets, one RPE value, one RIR value, equipment settings, a skipped action, pain, and an exercise note.

- [ ] **Step 5: Run append-session tests**

Run: `python -m unittest scripts.tests.test_append_session -v`

Expected: all tests pass and no file under the real `user-data/sessions` changes.

- [ ] **Step 6: Commit session-schema support**

```bash
git add scripts/append_session.py scripts/tests/test_append_session.py assets/starter-profile/example-session.json
git commit -m "feat: record pure coach workout sessions"
```

### Task 3: Implement deterministic coaching rules

**Files:**
- Create: `scripts/coach_rules.py`
- Create: `scripts/tests/test_coach_rules.py`

- [ ] **Step 1: Write failing rule tests**

Create tests that call `recommend_exercise(history, days_since_last)` and assert the following outputs:

```python
self.assertEqual(recommend_exercise([complete_12s], 3)["action"], "increase_minimum")
self.assertEqual(recommend_exercise([mid_range], 3)["action"], "hold_add_reps")
self.assertEqual(recommend_exercise([rpe_nine], 3)["action"], "reduce_5_10_percent")
self.assertEqual(recommend_exercise([painful], 3)["action"], "stop_or_substitute")
self.assertEqual(recommend_exercise([baseline], 10)["load_adjustment_percent"], -10)
self.assertEqual(recommend_exercise([baseline], 20)["load_adjustment_percent"], -20)
self.assertEqual(recommend_exercise([baseline], 35)["action"], "rebuild_baseline")
self.assertEqual(recommend_exercise(stagnant_three, 3)["action"], "review_stagnation")
self.assertEqual(recommend_exercise(declining_three, 3)["action"], "deload")
```

Each fixture is an exercise occurrence with `date`, `status`, `sets`, `pain`, `equipment`, and `settings`. Warm-up sets must not affect the decision.

- [ ] **Step 2: Run the rule tests and verify import failure**

Run: `python -m unittest scripts.tests.test_coach_rules -v`

Expected: `ModuleNotFoundError` for `scripts.coach_rules`.

- [ ] **Step 3: Implement the pure rule module**

Create `scripts/coach_rules.py` with these public functions:

```python
def working_sets(exercise):
    return [
        item for item in exercise.get("sets", [])
        if item.get("set_type", "working") == "working"
    ]


def session_signature(exercise):
    sets = working_sets(exercise)
    top_weight = max((item.get("weight_kg", 0) or 0 for item in sets), default=0)
    reps_at_top = sum(
        item.get("reps", 0) or 0 for item in sets
        if (item.get("weight_kg", 0) or 0) == top_weight
    )
    return top_weight, reps_at_top


def interruption_adjustment(days_since_last):
    if days_since_last is None or days_since_last < 7:
        return 0
    if days_since_last <= 14:
        return -10
    if days_since_last <= 30:
        return -20
    return None
```

`recommend_exercise` returns a JSON-safe dictionary containing `action`, `reason`, and `load_adjustment_percent`. Apply rules in this order:

1. latest pain severity above zero -> `stop_or_substitute`;
2. more than 30 days -> `rebuild_baseline`;
3. two consecutive top-load declines greater than 10% -> `deload`;
4. no improved `(top_weight, reps_at_top)` signature across three occurrences -> `review_stagnation`;
5. latest working set RPE at least 9 or any working set below 8 reps -> `reduce_5_10_percent`;
6. at least two working sets, all at least 12 reps, and maximum RPE no more than 8 -> `increase_minimum`;
7. otherwise -> `hold_add_reps`.

After choosing the action, combine the interruption percentage with the normal action. A 7–30 day interruption cannot produce `increase_minimum`; its action becomes `resume_reduced`. Store the exact triggering facts in `reason`.

- [ ] **Step 4: Run rule tests**

Run: `python -m unittest scripts.tests.test_coach_rules -v`

Expected: all rule tests pass.

- [ ] **Step 5: Commit the rule engine**

```bash
git add scripts/coach_rules.py scripts/tests/test_coach_rules.py
git commit -m "feat: add recovery aware coaching rules"
```

### Task 4: Build a pure-coach state snapshot

**Files:**
- Modify: `scripts/update_summary.py`
- Create: `scripts/tests/test_update_summary.py`
- Modify: `assets/starter-profile/CURRENT-STATE.json`

- [ ] **Step 1: Write the failing summary test**

Create two temporary session files for the same exercise and assert the updated state has this shape:

```python
self.assertEqual(state["profile"]["mode"], "pure_coach")
self.assertEqual(state["recovery"]["last_session_date"], "2026-09-12")
self.assertIn("seated_chest_press", state["exercise_history"])
self.assertIn("seated_chest_press", state["next_recommendations"])
self.assertIn("reason", state["next_recommendations"]["seated_chest_press"])
self.assertNotIn("exp", state["profile"])
self.assertNotIn("attributes", state)
self.assertNotIn("recent_bests", state)
```

Also assert that an exercise whose latest occurrence has pain appears once in `active_pain`, while pain followed by a later pain-free occurrence does not remain active.

- [ ] **Step 2: Run the summary test and verify failure**

Run: `python -m unittest scripts.tests.test_update_summary -v`

Expected: failure because the old state still contains RPG fields and lacks recommendations.

- [ ] **Step 3: Replace RPG aggregation with training aggregation**

`update_summary.py` must:

- load sessions in date order;
- group completed exercise occurrences by stable exercise name;
- retain the three most recent comparable occurrences per exercise in `exercise_history`;
- calculate recovery date, days since last training, recent overall RPE values, and active pain;
- call `recommend_exercise` for each exercise;
- preserve `profile.name` and force `profile.mode` to `pure_coach`;
- write only `schema_version`, `updated_at`, `profile`, `recovery`, `exercise_history`, and `next_recommendations`.

Use this state template in `assets/starter-profile/CURRENT-STATE.json`:

```json
{
  "schema_version": "2.0",
  "updated_at": null,
  "profile": {"name": "<你的名字>", "mode": "pure_coach"},
  "recovery": {
    "last_session_date": null,
    "days_since_last": null,
    "recent_rpe_trend": [],
    "active_pain": []
  },
  "exercise_history": {},
  "next_recommendations": {}
}
```

- [ ] **Step 4: Run summary tests**

Run: `python -m unittest scripts.tests.test_update_summary -v`

Expected: all tests pass.

- [ ] **Step 5: Commit the state rewrite**

```bash
git add scripts/update_summary.py scripts/tests/test_update_summary.py assets/starter-profile/CURRENT-STATE.json
git commit -m "feat: summarize training state without rpg data"
```

### Task 5: Initialize and validate pure-coach saves

**Files:**
- Modify: `scripts/init_profile.py`
- Modify: `scripts/validate_state.py`
- Create: `scripts/tests/test_profile_tools.py`
- Modify: `assets/starter-profile/PROFILE.md`
- Modify: `assets/starter-profile/CURRENT-PLAN.md`

- [ ] **Step 1: Write failing initialization and validation tests**

Tests must initialize into a temporary data directory and assert:

```python
self.assertEqual(result.returncode, 0)
self.assertEqual(state["profile"], {"name": "怀瑾", "mode": "pure_coach"})
self.assertNotIn("RPG", profile_text)
self.assertNotIn("教练体系", profile_text)
self.assertIn("全身 A", plan_text)
self.assertIn("全身 B", plan_text)
```

Validation tests must reject a state missing `recovery`, `exercise_history`, or `next_recommendations`, and must ignore any files under `story/`.

- [ ] **Step 2: Run profile-tool tests and verify failure**

Run: `python -m unittest scripts.tests.test_profile_tools -v`

Expected: failures because initialization still accepts a theme and validation expects RPG fields.

- [ ] **Step 3: Simplify initialization**

Remove `--theme`. Keep `--name` and `--force`, but make the destructive effect explicit in help and output. Initialization copies the starter profile and replaces only `<你的名字>` in `PROFILE.md` and `CURRENT-STATE.json`.

The starter `PROFILE.md` fields must be: name, optional baseline measures, goal, training level, equipment, realistic frequency, available duration, coaching mode, and injury or movement constraints.

The starter `CURRENT-PLAN.md` must contain sequential full-body A/B, two working sets of 8–12 reps, RPE 6–7 or RIR 3–4, 5–8 minutes of warm-up, and the rule that one weekly visit is success while two is ideal.

- [ ] **Step 4: Rewrite validation around the new schema**

Validate required top-level keys, `profile.mode == "pure_coach"`, non-negative `days_since_last`, RPE values from 1–10, RIR values from 0–10, pain severity from 0–10, and valid session dates. Do not inspect EXP, attributes, levels, or story references.

- [ ] **Step 5: Run profile-tool tests and the full isolated suite**

Run: `python -m unittest scripts.tests.test_profile_tools -v`

Run: `python scripts/test_regression.py`

Expected: all tests pass; the real `user-data` file hashes remain unchanged during both commands.

- [ ] **Step 6: Commit profile tools and templates**

```bash
git add scripts/init_profile.py scripts/validate_state.py scripts/tests/test_profile_tools.py assets/starter-profile/PROFILE.md assets/starter-profile/CURRENT-PLAN.md
git commit -m "feat: initialize pure coach profiles"
```

### Task 6: Make the AI behavior pure, concise, and traceable

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `examples/MINIMAL-RUN.md`
- Modify: `references/test-scenarios.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add manual behavior scenarios before rewriting instructions**

Document these expected conversations in `references/test-scenarios.md`:

1. “今天练” with no history -> full-body A plus conservative baseline instructions;
2. normal history -> complete plan first, with each load recommendation tied to the last result;
3. machine occupied -> one comparable substitute, not a redesigned whole workout;
4. poor sleep -> 5%–10% reduction or one fewer working set;
5. sharp pain -> stop the affected exercise and avoid diagnosis;
6. 10-day break -> 10% reduction;
7. three stagnant occurrences -> technique, rest, and exercise-fit review;
8. natural-language recap with missing RPE -> save RPE as absent rather than inventing it;
9. any coaching response -> no story, EXP, level, attribute, title, or named-coach imitation.

- [ ] **Step 2: Rewrite `SKILL.md` around the approved flow**

Keep these sections in order:

1. identity and scope;
2. training-first and adherence-first principles;
3. minimal initialization questions;
4. pre-workout file-reading order;
5. full-plan-first interaction;
6. training-time exception handling;
7. natural-language logging rules;
8. deterministic progression, recovery, interruption, and stagnation rules;
9. three-part recap format;
10. safety boundary and missing-data policy.

The file must explicitly say that named coaches are not selected, RPG files are ignored, missing data is not inferred, and every changed recommendation cites its training-data reason.

- [ ] **Step 3: Align user documentation**

Update `README.md` and `examples/MINIMAL-RUN.md` to describe the repository as a local pure-coach save for this workflow. Show this example interaction:

```text
用户：今天练。
教练：先告诉我昨晚睡眠、现在精神状态，以及是否有异常酸痛或疼痛。
用户：睡了 7 小时，精神 7/10，没有疼痛。
教练：今天进行全身 A。以下是完整计划；训练中只有器械占用、重量不合适或不适时再告诉我。
```

Remove unsupported claims that conversation alone becomes durable memory. Explain that durable continuity comes from the local session files and derived state.

- [ ] **Step 4: Record the conversion**

Add a dated changelog entry describing pure-coach mode, isolated tests, schema version 2.0, RPE/RIR logging, and recovery-aware recommendations.

- [ ] **Step 5: Review behavior text**

Run: `rg -n "剧情|经验值|EXP|等级|属性|周六野|凯圣王|帕梅拉" SKILL.md README.md examples/MINIMAL-RUN.md assets/starter-profile`

Expected: matches appear only in explicit statements that RPG and named-coach selection are disabled; no active instruction asks the coach to use them.

- [ ] **Step 6: Commit behavior and documentation**

```bash
git add SKILL.md README.md examples/MINIMAL-RUN.md references/test-scenarios.md CHANGELOG.md
git commit -m "docs: make pure coaching the active workflow"
```

### Task 7: Migrate the confirmed local profile without losing personal data

**Files:**
- Modify, ignored: `user-data/PROFILE.md`
- Modify, ignored: `user-data/CURRENT-PLAN.md`
- Modify, ignored: `user-data/CURRENT-STATE.json`

- [ ] **Step 1: Capture pre-migration hashes and content**

Run:

```powershell
Get-FileHash user-data/PROFILE.md,user-data/CURRENT-PLAN.md,user-data/CURRENT-STATE.json
Get-Content -Raw user-data/PROFILE.md
Get-Content -Raw user-data/CURRENT-PLAN.md
Get-Content -Raw user-data/CURRENT-STATE.json
```

Expected: the profile contains 怀瑾, age 22, 180 cm, 73.5 kg reference weight, body-composition baseline, 1–2 weekly sessions, 40–60 minutes, and the currently asymptomatic knee note.

- [ ] **Step 2: Update only fields required by schema 2.0**

Preserve all confirmed personal facts. Ensure:

- `PROFILE.md` says pure coach mode and contains no named coach or RPG theme;
- `CURRENT-PLAN.md` contains sequential full-body A/B and the approved progression rules;
- `CURRENT-STATE.json` has `schema_version: "2.0"`, `profile.name: "怀瑾"`, `profile.mode: "pure_coach"`, and empty derived collections when no real sessions exist.

Do not create a workout session to represent planning, sleep loss, or a test.

- [ ] **Step 3: Validate the live profile without changing it**

Run: `python scripts/validate_state.py`

Expected: exit code 0 with `[OK]` output.

Run: `git status --short`

Expected: no `user-data` files appear because personal data remains ignored. Do not commit ignored personal data.

### Task 8: End-to-end verification

**Files:**
- Verify all files changed above

- [ ] **Step 1: Snapshot live personal-data hashes**

Run:

```powershell
$before = Get-FileHash user-data/PROFILE.md,user-data/CURRENT-PLAN.md,user-data/CURRENT-STATE.json
$before | Format-Table Path,Hash
```

- [ ] **Step 2: Run the complete isolated test suite**

Run: `python scripts/test_regression.py`

Expected: all tests pass with no Unicode encoding exception.

- [ ] **Step 3: Prove tests did not touch live data**

Run:

```powershell
$after = Get-FileHash user-data/PROFILE.md,user-data/CURRENT-PLAN.md,user-data/CURRENT-STATE.json
Compare-Object $before $after -Property Path,Hash
```

Expected: no output.

- [ ] **Step 4: Run static and state checks**

Run: `python scripts/validate_state.py`

Expected: exit code 0.

Run: `python -m compileall -q scripts`

Expected: exit code 0.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 5: Perform the nine manual behavior scenarios**

Read `SKILL.md`, the live profile, plan, state, and temporary fixture sessions. For each scenario in `references/test-scenarios.md`, record pass or fail in the command output or implementation notes. Do not write fixture sessions into live `user-data`.

- [ ] **Step 6: Commit any verification-only corrections**

If verification required a correction, stage only the relevant project files and commit:

```bash
git add SKILL.md README.md CHANGELOG.md assets scripts examples references
git commit -m "fix: complete pure coach verification"
```

If no correction was required, do not create an empty commit.

- [ ] **Step 7: Report completion evidence**

Report the number of automated tests passed, the state-validation result, confirmation that personal-data hashes were unchanged by tests, the manual-scenario result, and the commit hashes. Do not claim the four-week coaching outcome is validated until four weeks of real use have occurred.
