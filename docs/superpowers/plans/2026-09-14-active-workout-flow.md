# Active Workout Startup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `开始训练` generate one validated, session-specific Active Workout and open it in the system default browser, while keeping long-term planning in project files and removing the fixed pre-workout questionnaire.

**Architecture:** Separate long-term state (`PROFILE.md`, `CURRENT-PLAN.md`, `CURRENT-STATE.json`, sessions) from the ephemeral Active Workout (`current-workout.js`). Add a dedicated Active Workout validator and a dedicated browser launcher; the visualizer renders only the final session-specific prescription. `SKILL.md` and `AGENTS.md` define the conversational orchestration, but deterministic validation/opening behavior stays in Python scripts.

**Tech Stack:** Python 3.8+ standard library, browser-native HTML/CSS/JavaScript, `unittest`, Markdown project instructions.

**Spec:** `docs/superpowers/specs/2026-09-14-active-workout-flow-design.md`

> **Post-review correction:** The final validator and launcher require `--session-id <本次 sessionId>`. This expected ID must match the generated card, preventing a same-day previous session from being opened when a new card was not successfully written. Earlier illustrative code blocks in this implementation record are superseded by that invariant.

## Global Constraints

- Keep the project local-file driven; do not add a server, database, npm build, or third-party Python dependency.
- `user-data/` and generated `extensions/exercise-visualizer/current-workout.js` remain local/untracked personal data.
- A temporary same-day adjustment changes only the Active Workout unless the user explicitly asks to change the long-term plan.
- Normal `开始训练` must not force the fixed sleep / energy / pain questionnaire.
- If the first user message already contains relevant status information, do not ask for it again.
- The complete executable prescription appears in the browser training page; chat should not duplicate the full workout after opening it.
- Do not add set checkboxes, weight/reps input, rest timers, completion buttons, dashboards, voice control, pose estimation, or workout logging UI in this iteration.
- Browser opening must use the OS default browser; Codex `open_in_codex` is not an acceptable default substitute.
- Existing test isolation via `FITNESS_COACH_DATA_DIR` / `FITNESS_COACH_VISUALIZER_DIR` must remain intact.

---

### Task 1: Separate onboarding validation from Active Workout validation

**Files:**
- Create: `scripts/validate_workout.py`
- Create: `scripts/tests/test_active_workout.py`
- Modify: `scripts/validate_onboarding.py`
- Modify: `scripts/tests/test_profile_tools.py`
- Modify: `extensions/exercise-visualizer/current-workout.example.js`

**Interfaces:**
- Consumes: `FITNESS_COACH_VISUALIZER_DIR` environment override and `current-workout.js` JavaScript wrapper.
- Produces: `validate_workout.load_workout(path: Path) -> dict` and `validate_workout.validate_workout(workout: dict) -> list[str]`; CLI exits `0` on a valid Active Workout and `1` otherwise.
- Active Workout schema `2.0` fields:
  - top-level: `schemaVersion`, `initialized`, `sessionId`, `generatedAt`, `planLabel`, `name`, `status`, `notes`, `exercises`;
  - each exercise: `order`, `name`, `prescription`;
  - each exercise prescription: positive numeric `sets`, non-empty string `reps`, non-empty string `rpe`;
  - optional exercise `notes` is an array of strings.

- [ ] **Step 1: Add failing Active Workout validator tests**

Create `scripts/tests/test_active_workout.py` with the following core cases:

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
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
        return {
            "schemaVersion": "2.0",
            "initialized": True,
            "sessionId": "20260914-113000-full-body-a",
            "generatedAt": "2026-09-14T11:30:00+08:00",
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
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
python -m unittest scripts.tests.test_active_workout -v
```

Expected: FAIL because `scripts/validate_workout.py` does not exist.

- [ ] **Step 3: Implement the dedicated Active Workout validator**

Create `scripts/validate_workout.py` with this structure:

```python
#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)


def load_workout(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.CURRENT_WORKOUT\s*=\s*Object\.freeze\(\s*(\{.*\})\s*\)\s*;",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("current-workout.js 必须把合法 JSON 赋给 window.CURRENT_WORKOUT")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ValueError(f"current-workout.js 的 JSON 格式错误: {error.msg}")


def validate_workout(workout):
    errors = []
    if workout.get("schemaVersion") != "2.0":
        errors.append("schemaVersion 必须为 2.0")
    if workout.get("initialized") is not True:
        errors.append("initialized 必须为 true")
    for key in ("sessionId", "generatedAt", "planLabel", "name", "status"):
        if not isinstance(workout.get(key), str) or not workout[key].strip():
            errors.append(f"{key} 不能为空")
    generated_at = workout.get("generatedAt")
    if isinstance(generated_at, str) and generated_at.strip():
        try:
            datetime.fromisoformat(generated_at)
        except ValueError:
            errors.append("generatedAt 必须是 ISO 8601 时间")
    if not isinstance(workout.get("notes"), list):
        errors.append("notes 必须是数组")
    exercises = workout.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        errors.append("exercises 必须至少包含一个动作")
        return errors
    for index, exercise in enumerate(exercises, start=1):
        if not isinstance(exercise, dict):
            errors.append(f"第{index}个动作格式错误")
            continue
        if not isinstance(exercise.get("order"), int) or isinstance(exercise.get("order"), bool) or exercise["order"] <= 0:
            errors.append(f"第{index}个动作 order 必须为正整数")
        if not isinstance(exercise.get("name"), str) or not exercise["name"].strip():
            errors.append(f"第{index}个动作 name 不能为空")
        prescription = exercise.get("prescription")
        if not isinstance(prescription, dict):
            errors.append(f"第{index}个动作 prescription 格式错误")
            continue
        sets = prescription.get("sets")
        if not isinstance(sets, (int, float)) or isinstance(sets, bool) or sets <= 0:
            errors.append(f"第{index}个动作 prescription.sets 必须大于 0")
        for key in ("reps", "rpe"):
            value = prescription.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"第{index}个动作 prescription.{key} 不能为空")
        if "notes" in exercise and not isinstance(exercise["notes"], list):
            errors.append(f"第{index}个动作 notes 必须是数组")
    return errors


def main():
    path = VISUALIZER / "current-workout.js"
    if not path.exists():
        print("[ERROR] current-workout.js 不存在")
        return 1
    try:
        workout = load_workout(path)
    except ValueError as error:
        print(f"[ERROR] {error}")
        return 1
    errors = validate_workout(workout)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] Active Workout 有效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Make onboarding validation stop requiring an active session**

In `scripts/validate_onboarding.py`:

- remove `json`, `os`, and visualizer-only imports/constants if no longer used;
- remove `REQUIRED_WORKOUT_KEYS`;
- delete `validate_workout(errors)`;
- make `main()` validate only profile + long-term plan.

In `scripts/tests/test_profile_tools.py`:

- change `write_completed_onboarding()` so it no longer needs to write an initialized workout card;
- remove `workout_missing`, `workout_not_initialized`, `workout_malformed`, and `workout_unassigned` from `test_onboarding_validator_rejects_each_incomplete_artifact`;
- change `test_skill_marks_generated_workout_card_as_initialized` later in Task 4 so it tests the new start-training flow instead of onboarding.

This preserves the invariant: onboarding proves the long-term profile/plan exists; `validate_workout.py` proves one specific training session exists.

- [ ] **Step 5: Upgrade the public blank workout example to schema 2.0**

Replace `extensions/exercise-visualizer/current-workout.example.js` payload with:

```javascript
(function () {
  "use strict";

  window.CURRENT_WORKOUT = Object.freeze({
    "schemaVersion": "2.0",
    "initialized": false,
    "sessionId": "",
    "generatedAt": "",
    "planLabel": "尚未生成",
    "name": "请先开始训练",
    "status": "等待生成本次训练",
    "notes": [],
    "exercises": []
  });
})();
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest scripts.tests.test_active_workout scripts.tests.test_profile_tools -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate_workout.py scripts/validate_onboarding.py scripts/tests/test_active_workout.py scripts/tests/test_profile_tools.py extensions/exercise-visualizer/current-workout.example.js
git commit -m "feat: separate active workout validation"
```

---

### Task 2: Make the browser page render the final per-exercise Active Workout

**Files:**
- Modify: `extensions/exercise-visualizer/index.html`
- Modify: `scripts/tests/test_profile_tools.py`

**Interfaces:**
- Consumes: schema `2.0` `window.CURRENT_WORKOUT` from Task 1.
- Produces: browser page that renders `exercise.prescription.sets`, `.reps`, `.rpe`, and optional `exercise.notes`, plus top-level session status/notes.

- [ ] **Step 1: Add failing static-contract tests for the visualizer**

Add to `scripts/tests/test_profile_tools.py`:

```python
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
```

- [ ] **Step 2: Run the focused visualizer tests to verify they fail**

Run:

```bash
python -m unittest scripts.tests.test_profile_tools.ProfileToolTests.test_visualizer_renders_per_exercise_prescription scripts.tests.test_profile_tools.ProfileToolTests.test_visualizer_identifies_active_session -v
```

Expected: FAIL because `index.html` still reads the old global `workout.prescription` object.

- [ ] **Step 3: Replace the global prescription summary**

In `extensions/exercise-visualizer/index.html`, remove the hero badges that assume one uniform prescription:

```javascript
workout.prescription.sets + " 组 × " + workout.prescription.reps + " 次",
"目标 RPE " + workout.prescription.rpe
```

Use session-level summary instead:

```javascript
[
  workout.exercises.length + " 个动作",
  workout.status,
  "Session " + workout.sessionId
].forEach(function (text) {
  const badge = document.createElement("span");
  badge.textContent = text;
  summary.appendChild(badge);
});
```

- [ ] **Step 4: Render each action's final prescription**

When building each exercise card, replace global metrics with:

```javascript
const prescription = exercise.prescription;
addMetric(metrics, "正式组", prescription.sets);
addMetric(metrics, "次数", prescription.reps);
addMetric(metrics, "目标 RPE", prescription.rpe);
```

Render optional exercise notes below the metrics:

```javascript
if (Array.isArray(exercise.notes) && exercise.notes.length) {
  const block = document.createElement("div");
  block.className = "instructions-block";
  const heading = document.createElement("h3");
  heading.textContent = "本次提示";
  block.appendChild(heading);
  const list = document.createElement("ul");
  exercise.notes.forEach(function (note) {
    const item = document.createElement("li");
    item.textContent = note;
    list.appendChild(item);
  });
  block.appendChild(list);
  body.appendChild(block);
}
```

Keep the existing GIF loading, translated metadata, instructions, and text-only fallback behavior unchanged.

- [ ] **Step 5: Update the uninitialized state copy**

Change the empty-state message from “先初始化健身教练” to a distinction between profile initialization and session generation:

```text
尚未生成本次训练。若个人档案尚未初始化，请先初始化健身教练；否则回到项目对话输入“开始训练”。
```

Set the title to `请先生成本次训练` rather than implying initialization always failed.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest scripts.tests.test_profile_tools -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add extensions/exercise-visualizer/index.html scripts/tests/test_profile_tools.py
git commit -m "feat: render active workout prescriptions"
```

---

### Task 3: Add a deterministic default-browser launcher

**Files:**
- Create: `scripts/open_workout.py`
- Create: `scripts/tests/test_open_workout.py`

**Interfaces:**
- Consumes: valid `current-workout.js` and `validate_workout.load_workout` from Task 1.
- Produces: `build_workout_url(index_path: Path, session_id: str) -> str`; CLI validates the Active Workout before invoking `webbrowser.open(url, new=2)`.

- [ ] **Step 1: Write failing launcher tests**

Create `scripts/tests/test_open_workout.py`:

```python
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "open_workout.py"


def load_module():
    spec = importlib.util.spec_from_file_location("open_workout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenWorkoutTests(unittest.TestCase):
    def test_build_workout_url_contains_session_query(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "index.html"
            index.write_text("<html></html>", encoding="utf-8")
            url = module.build_workout_url(index, "session-123")
        self.assertTrue(url.startswith("file:"))
        self.assertIn("session=session-123", url)

    def test_main_uses_default_browser_only_after_validation(self):
        module = load_module()
        with mock.patch.object(module, "validate_active_workout", return_value="session-123"), \
             mock.patch.object(module.webbrowser, "open", return_value=True) as browser:
            result = module.main()
        self.assertEqual(result, 0)
        browser.assert_called_once()
        self.assertEqual(browser.call_args.kwargs["new"], 2)

    def test_main_does_not_open_browser_when_validation_fails(self):
        module = load_module()
        with mock.patch.object(module, "validate_active_workout", side_effect=ValueError("bad workout")), \
             mock.patch.object(module.webbrowser, "open") as browser:
            result = module.main()
        self.assertEqual(result, 1)
        browser.assert_not_called()
```

- [ ] **Step 2: Run the launcher tests to verify they fail**

Run:

```bash
python -m unittest scripts.tests.test_open_workout -v
```

Expected: FAIL because `scripts/open_workout.py` does not exist.

- [ ] **Step 3: Implement the browser launcher**

Create `scripts/open_workout.py`:

```python
#!/usr/bin/env python3
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_workout import load_workout, validate_workout

ROOT = Path(__file__).resolve().parent.parent
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)


def validate_active_workout():
    workout_path = VISUALIZER / "current-workout.js"
    if not workout_path.exists():
        raise ValueError("current-workout.js 不存在")
    workout = load_workout(workout_path)
    errors = validate_workout(workout)
    if errors:
        raise ValueError("；".join(errors))
    return workout["sessionId"]


def build_workout_url(index_path, session_id):
    return index_path.resolve().as_uri() + "?" + urlencode({"session": session_id})


def main():
    index_path = VISUALIZER / "index.html"
    if not index_path.exists():
        print("[ERROR] 训练页 index.html 不存在")
        return 1
    try:
        session_id = validate_active_workout()
    except ValueError as error:
        print(f"[ERROR] {error}")
        return 1
    url = build_workout_url(index_path, session_id)
    if not webbrowser.open(url, new=2):
        print(f"[ERROR] 默认浏览器未能打开训练页：{url}")
        return 1
    print(f"[OK] 已在默认浏览器打开 Active Workout：{session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run launcher tests**

Run:

```bash
python -m unittest scripts.tests.test_open_workout -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/open_workout.py scripts/tests/test_open_workout.py
git commit -m "feat: open workout in default browser"
```

---

### Task 4: Change the coach orchestration from fixed questionnaire to Active Workout start flow

**Files:**
- Modify: `SKILL.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `scripts/tests/test_profile_tools.py`

**Interfaces:**
- Consumes: `python scripts/validate_workout.py` and `python scripts/open_workout.py` from Tasks 1 and 3.
- Produces: deterministic conversational instructions for planning chats vs training chats and the exact order of operations for `开始训练`.

- [ ] **Step 1: Add failing instruction-contract tests**

Add these tests to `scripts/tests/test_profile_tools.py`:

```python
def test_skill_does_not_force_fixed_preworkout_questionnaire(self):
    skill = SKILL.read_text(encoding="utf-8")
    self.assertNotIn("只补问睡眠、精神状态、异常酸痛或疼痛。随后一次性给出完整计划", skill)
    self.assertIn("默认不固定询问睡眠、精神状态和疼痛", skill)
    self.assertIn("用户已主动提供的信息不得重复追问", skill)


def test_skill_builds_and_validates_active_workout_before_opening(self):
    skill = SKILL.read_text(encoding="utf-8")
    self.assertIn("Active Workout", skill)
    self.assertIn("python scripts/validate_workout.py", skill)
    self.assertIn("python scripts/open_workout.py", skill)
    self.assertIn("聊天不重复输出完整训练处方", skill)


def test_readme_explains_planning_and_training_conversations(self):
    readme = README.read_text(encoding="utf-8")
    self.assertIn("规划对话", readme)
    self.assertIn("训练对话", readme)
    self.assertIn("开始训练", readme)
    self.assertIn("默认浏览器", readme)
```

- [ ] **Step 2: Run instruction-contract tests to verify they fail**

Run:

```bash
python -m unittest scripts.tests.test_profile_tools.ProfileToolTests.test_skill_does_not_force_fixed_preworkout_questionnaire scripts.tests.test_profile_tools.ProfileToolTests.test_skill_builds_and_validates_active_workout_before_opening scripts.tests.test_profile_tools.ProfileToolTests.test_readme_explains_planning_and_training_conversations -v
```

Expected: FAIL against the current fixed-three-question flow.

- [ ] **Step 3: Rewrite the `SKILL.md` training-start section**

Replace the current “训练前读取顺序” behavior with explicit orchestration equivalent to:

```markdown
## 开始训练与 Active Workout

用户说“开始训练”“今天练”或同义表达时：

1. 读取 `PROFILE.md`、`CURRENT-STATE.json`、`CURRENT-PLAN.md`，只在摘要不足时读取相关 session；
2. 默认不固定询问睡眠、精神状态和疼痛。用户没有主动报告异常状态时，直接依据长期计划和历史表现生成本次训练；
3. 用户已主动提供的信息不得重复追问。只有用户报告了会影响训练的异常、但信息不足以做安全决策时，才补问最少必要信息；
4. 把今天最终执行的处方写入 `extensions/exercise-visualizer/current-workout.js`。它是 Active Workout 快照，不是长期计划副本；
5. 每个动作单独写入 `prescription.sets`、`prescription.reps`、`prescription.rpe`，并写入 `sessionId`、`generatedAt`、`status`、`notes`；
6. 运行 `python scripts/validate_workout.py`。校验失败时先修正，禁止打开旧训练卡冒充今天的训练；
7. 校验通过后运行 `python scripts/open_workout.py`，必须交给系统默认浏览器；不要用编辑器打开 `index.html` 代替训练页；
8. 浏览器打开后，聊天不重复输出完整训练处方，只简短说明今天训练名称和异常情况下何时回来询问。

本次疲劳、器械占用或其他临时调整默认只改变 Active Workout，不修改 `CURRENT-PLAN.md`。用户明确说“以后”“调整长期计划”“改成每周 X 次”等时，才进入规划任务并写回长期文件。
```

Also remove onboarding language that requires generation of an initialized workout card and `validate_onboarding.py` to prove the card exists. Onboarding should finish after profile + long-term plan validation; the first Active Workout is created when the user actually starts training.

- [ ] **Step 4: Tighten `AGENTS.md` entry rules**

Add concise root-level rules equivalent to:

```markdown
- “开始训练 / 今天练”等请求进入 Active Workout 流程：读取长期文件，生成本次训练，运行 `validate_workout.py`，再运行 `open_workout.py`。
- 默认不执行固定训练前三问；只在用户主动报告异常且信息不足以改变处方时补问最少必要信息。
- 训练页必须由系统默认浏览器打开；不要用 Codex 编辑器打开 `index.html` 代替训练页面。
- 长期计划变更必须写回项目文件；聊天上下文不是训练事实来源。
```

- [ ] **Step 5: Update README usage model**

Add a short “两类对话” section:

```markdown
## 两类对话

- **规划对话**：调整目标、频率、动作和阶段计划，最终写回 `PROFILE.md` / `CURRENT-PLAN.md`。
- **训练对话**：每次都可以新建。输入“开始训练”，AI 从项目文件恢复状态，生成今天的 Active Workout，并在系统默认浏览器打开训练页。

项目文件是长期存档，对话只是操作入口；不需要维护一个永远续聊的训练线程。
```

Update the daily-use example so normal flow is:

```text
用户：开始训练。
教练：今天是全身 A，训练页已在默认浏览器打开。正常训练不用回这里；器械占用、重量不合适或身体不适时再告诉我。
```

Keep a second example showing `开始训练，昨晚 6.5 小时，精神一般，无痛` proceeds without repeat questions.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest scripts.tests.test_profile_tools -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add SKILL.md AGENTS.md README.md scripts/tests/test_profile_tools.py
git commit -m "feat: streamline active workout start flow"
```

---

### Task 5: Full regression and end-to-end dry-run contract

**Files:**
- Modify: `scripts/test_regression.py` only if new test modules are not already discovered by its current test discovery.
- No production feature expansion.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: one regression command proving legacy recording/state behavior plus Active Workout startup components coexist.

- [ ] **Step 1: Run the existing regression entry point**

Run:

```bash
python scripts/test_regression.py
```

Expected: all existing and newly discovered tests PASS. If `test_regression.py` enumerates modules rather than using discovery, add `scripts.tests.test_active_workout` and `scripts.tests.test_open_workout` to that list and rerun.

- [ ] **Step 2: Run the explicit new-flow test set**

Run:

```bash
python -m unittest scripts.tests.test_active_workout scripts.tests.test_open_workout scripts.tests.test_profile_tools -v
```

Expected: PASS.

- [ ] **Step 3: Perform a local dry run without touching real user data**

Use a temporary data directory and visualizer directory, initialize a test profile, write a valid schema-2.0 Active Workout fixture, then run validators. Do **not** use the real `user-data` directory.

PowerShell example:

```powershell
$root = (Get-Location).Path
$temp = Join-Path $env:TEMP "fitness-active-workout-dryrun"
Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $temp | Out-Null
$env:FITNESS_COACH_DATA_DIR = Join-Path $temp "data"
$env:FITNESS_COACH_VISUALIZER_DIR = Join-Path $temp "visualizer"
python scripts/init_profile.py --name 测试用户
# Copy index.html/exercise-map.js into the temp visualizer only if testing the launcher against the temp override.
python scripts/validate_state.py
python scripts/validate_onboarding.py
python scripts/validate_workout.py
```

For the final browser-opening smoke test on the developer machine, use a disposable valid `current-workout.js` in the normal visualizer path only if no real Active Workout exists, then restore/delete it immediately after the test. Do not overwrite a user's real workout card.

- [ ] **Step 4: Verify git status contains no personal data**

Run:

```bash
git status --short
```

Expected: no `user-data/` file and no generated `extensions/exercise-visualizer/current-workout.js` appears as tracked/untracked work intended for commit.

- [ ] **Step 5: Final commit if Task 5 required test-runner changes**

Only if `scripts/test_regression.py` was modified:

```bash
git add scripts/test_regression.py
git commit -m "test: include active workout regression coverage"
```

If no file change was needed, do not create an empty commit.

---

## Final Acceptance Checklist

- [ ] Opening the repository at `fitness-coach-rpg` root makes new training conversations load the project rules.
- [ ] `开始训练` does not force the fixed three-question pre-workout questionnaire.
- [ ] `开始训练，6.5h，一般，无痛` does not ask the same questions again.
- [ ] `今天特别累` may trigger only the minimum clarifying information needed for a safe adjustment.
- [ ] The long-term plan remains in `CURRENT-PLAN.md`; temporary session changes do not mutate it.
- [ ] `current-workout.js` schema `2.0` describes one Active Workout with per-exercise prescriptions.
- [ ] Invalid or stale Active Workout data, including a same-day session ID mismatch, prevents browser opening rather than silently showing an old card.
- [ ] The training page renders the final per-exercise prescription and GIF/text fallback in one place.
- [ ] `open_workout.py` opens the training page through the OS default browser with a session query parameter.
- [ ] Chat does not duplicate the full workout after the browser page opens.
- [ ] Existing session append, summary, state validation, and data-isolation tests still pass.
- [ ] No new training-in-progress features are added before real-world testing reveals the need.
