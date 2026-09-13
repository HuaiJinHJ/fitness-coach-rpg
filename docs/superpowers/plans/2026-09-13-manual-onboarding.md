# Manual Personalized Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Fork 用户主动说“初始化健身教练”后得到自己的档案、训练结构和本地 GIF 训练卡，不继承仓库作者的个人处方。

**Architecture:** 公开仓库只保存中性数据模板、通用 GIF 映射和定制说明。`init_profile.py` 负责建立空白合法档案并准备一个被 Git 忽略的本地训练卡文件；AI 根据初始化问答写入个性化档案、计划和训练卡。可视化页面在未初始化时显示明确引导，不再回退到作者计划。

**Tech Stack:** Python 3.8+ 标准库、Markdown、原生 JavaScript、`unittest`、Git。

---

## 文件结构

- 修改 `assets/starter-profile/CURRENT-PLAN.md`：中性计划结构，不含固定训练拆分或动作。
- 修改 `scripts/tests/test_profile_tools.py`：验证空白初始化不携带作者处方，并验证本地训练卡的创建与覆盖保护。
- 修改 `scripts/init_profile.py`：初始化时复制本地训练卡模板，不替用户决定计划。
- 修改 `.gitignore`：忽略个性化 `extensions/exercise-visualizer/current-workout.js`。
- 重命名 `extensions/exercise-visualizer/current-workout.js` 为 `current-workout.example.js`：提交中性、未初始化的回退模板。
- 修改 `extensions/exercise-visualizer/index.html`：缺少或尚未生成训练卡时引导用户初始化。
- 创建 `references/exercise-gif-customization.md`：说明素材来源、动作 ID、映射和验证方法。
- 修改 `SKILL.md`：定义手动触发、问答、写档、生成计划和训练卡的完整流程。
- 修改 `AGENTS.md`：先判断初始化状态，再读取个人文件。
- 修改 `README.md`：增加第一次使用与 GIF 定制入口，去掉个人计划式默认描述。
- 修改 `CHANGELOG.md`：记录初始化与数据隔离变化。

### Task 1: 将初始化模板改为中性结构

**Files:**
- Modify: `scripts/tests/test_profile_tools.py`
- Modify: `assets/starter-profile/CURRENT-PLAN.md`

- [ ] **Step 1: 把原初始化测试改成中性模板断言**

将 `test_initializes_pure_coach_profile_and_sequential_plan` 改名为 `test_initializes_blank_personalized_profile`，并使用以下断言：

```python
def test_initializes_blank_personalized_profile(self):
    result = self.initialize()
    self.assertEqual(result.returncode, 0, result.stderr)
    state = json.loads((self.data_dir / "CURRENT-STATE.json").read_text(encoding="utf-8"))
    profile = (self.data_dir / "PROFILE.md").read_text(encoding="utf-8")
    plan = (self.data_dir / "CURRENT-PLAN.md").read_text(encoding="utf-8")
    self.assertEqual(state["profile"], {"name": "怀瑾", "mode": "pure_coach"})
    self.assertNotIn("RPG", profile)
    self.assertNotIn("教练体系", profile)
    for personalized_default in ("全身 A", "全身 B", "坐姿推胸", "坐姿划船", "罗马尼亚硬拉", "腿举"):
        self.assertNotIn(personalized_default, plan)
    self.assertIn("训练目标", plan)
    self.assertIn("每周频率", plan)
    self.assertIn("动作安排", plan)
    self.assertFalse((self.data_dir / "story").exists())
```

- [ ] **Step 2: 运行单项测试，确认旧模板导致失败**

Run:

```powershell
$env:FITNESS_COACH_DATA_DIR = Join-Path $env:TEMP 'fitness-coach-plan-red'
python -m unittest scripts.tests.test_profile_tools.ProfileToolTests.test_initializes_blank_personalized_profile -v
Remove-Item Env:FITNESS_COACH_DATA_DIR
```

Expected: FAIL，失败证据包含旧模板中的 `全身 A`。

- [ ] **Step 3: 用中性计划字段替换 starter plan**

将 `assets/starter-profile/CURRENT-PLAN.md` 完整替换为：

```markdown
# 当前计划 CURRENT-PLAN

> 初始化完成前不提供训练处方。计划必须根据用户明确提供的目标、经验、器械、频率、时长和动作限制生成。

## 计划依据

- **训练目标**：`<待初始化>`
- **训练经验**：`<待初始化>`
- **训练地点与器械**：`<待初始化>`
- **每周频率**：`<待初始化>`
- **单次时长**：`<待初始化>`
- **疼痛、旧伤或动作限制**：`<待初始化>`

## 当前阶段

- **阶段名称**：`<待初始化>`
- **阶段目标**：`<待初始化>`
- **复盘时间**：`<待初始化>`

## 动作安排

`<初始化后生成；写明训练日顺序、动作、组数、次数范围、选重方法及 RPE/RIR 目标>`

## 调整与安全边界

`<初始化后根据个人条件生成>`
```

- [ ] **Step 4: 运行单项测试，确认中性初始化通过**

Run: 与 Step 2 相同。

Expected: PASS。

- [ ] **Step 5: 提交中性模板**

```powershell
git add -- assets/starter-profile/CURRENT-PLAN.md scripts/tests/test_profile_tools.py
git commit -m "fix: remove personal plan from starter profile"
```

### Task 2: 隔离本地 GIF 训练卡

**Files:**
- Modify: `.gitignore`
- Rename: `extensions/exercise-visualizer/current-workout.js` → `extensions/exercise-visualizer/current-workout.example.js`
- Modify: `scripts/init_profile.py`
- Modify: `scripts/tests/test_profile_tools.py`

- [ ] **Step 1: 增加训练卡初始化和覆盖保护测试**

在 `ProfileToolTests` 中加入：

```python
def test_initialization_creates_untracked_blank_workout_card(self):
    result = self.initialize()
    self.assertEqual(result.returncode, 0, result.stderr)
    card = (self.visualizer_dir / "current-workout.js").read_text(encoding="utf-8")
    self.assertIn('initialized: false', card)
    self.assertNotIn("坐姿推胸", card)

def test_existing_profile_is_not_overwritten(self):
    self.assertEqual(self.initialize().returncode, 0)
    profile_path = self.data_dir / "PROFILE.md"
    profile_path.write_text("我的现有档案", encoding="utf-8")
    second = self.run_tool(INIT, "--name", "其他人")
    self.assertNotEqual(second.returncode, 0)
    self.assertEqual(profile_path.read_text(encoding="utf-8"), "我的现有档案")
```

在 `setUp` 中为可视化训练卡使用临时路径，避免测试写入仓库：

```python
self.visualizer_dir = Path(self.temp.name) / "visualizer"
self.env["FITNESS_COACH_VISUALIZER_DIR"] = str(self.visualizer_dir)
```

- [ ] **Step 2: 运行新增测试，确认训练卡尚未创建**

Run:

```powershell
python -m unittest scripts.tests.test_profile_tools.ProfileToolTests.test_initialization_creates_untracked_blank_workout_card scripts.tests.test_profile_tools.ProfileToolTests.test_existing_profile_is_not_overwritten -v
```

Expected: 第一项 FAIL，第二项 PASS。

- [ ] **Step 3: 建立中性训练卡模板和忽略规则**

将现有训练卡重命名为 `current-workout.example.js`，内容替换为：

```javascript
(function () {
  "use strict";

  window.CURRENT_WORKOUT = Object.freeze({
    schemaVersion: "1.0",
    initialized: false,
    planLabel: "尚未初始化",
    name: "请先初始化健身教练",
    status: "需要个人训练计划",
    prescription: { sets: null, reps: "", rpe: "" },
    notes: [],
    exercises: []
  });
})();
```

在 `.gitignore` 增加：

```gitignore
# 本地个性化 GIF 训练卡
extensions/exercise-visualizer/current-workout.js
```

- [ ] **Step 4: 让初始化脚本复制本地训练卡模板**

在 `scripts/init_profile.py` 中增加：

```python
VISUALIZER = Path(
    os.environ.get(
        "FITNESS_COACH_VISUALIZER_DIR",
        ROOT / "extensions" / "exercise-visualizer",
    )
)
WORKOUT_TEMPLATE = ROOT / "extensions" / "exercise-visualizer" / "current-workout.example.js"
```

补充 `import os`，并在用户档案复制完成后执行：

```python
VISUALIZER.mkdir(parents=True, exist_ok=True)
shutil.copy2(WORKOUT_TEMPLATE, VISUALIZER / "current-workout.js")
```

- [ ] **Step 5: 运行新增测试和完整 profile 测试**

Run:

```powershell
python -m unittest scripts.tests.test_profile_tools -v
```

Expected: 全部 PASS，测试训练卡只出现在临时目录。

- [ ] **Step 6: 验证本地训练卡确实被 Git 忽略并提交**

Run:

```powershell
git check-ignore -v extensions/exercise-visualizer/current-workout.js
```

Expected: 输出 `.gitignore` 中对应规则。

Commit:

```powershell
git add -- .gitignore scripts/init_profile.py scripts/tests/test_profile_tools.py extensions/exercise-visualizer/current-workout.example.js
git commit -m "feat: isolate personalized workout cards"
```

### Task 3: 明确手动初始化的 AI 行为

**Files:**
- Modify: `SKILL.md`
- Modify: `AGENTS.md`
- Modify: `README.md`

- [ ] **Step 1: 更新 `SKILL.md` 初始化章节**

用以下流程替换现有“初始化”章节，并删除“默认使用全身 A/B”的全局要求：

```markdown
## 手动初始化

仅在用户明确说“初始化健身教练”或同义请求时开始，不因普通健身咨询擅自创建档案。

先检查 `user-data/`。目录不存在或仍为空模板时，一次询问：主要目标、训练经验、训练地点与器械、每周现实频率、单次时长、当前疼痛、旧伤或动作限制。姓名、年龄、身高和体重为选填项，不阻塞初始化。

收到必要信息后：

1. 运行 `python scripts/init_profile.py --name <用户提供姓名>`；未提供姓名时省略 `--name`；
2. 把用户明确提供的信息写入 `user-data/PROFILE.md` 和 `CURRENT-STATE.json`；
3. 根据目标、经验、器械、频率、时长和动作限制生成 `user-data/CURRENT-PLAN.md`；
4. 生成 `extensions/exercise-visualizer/current-workout.js`，格式参考 `current-workout.example.js`；只映射当前计划中已确认的动作；
5. 运行 `python scripts/validate_state.py`；
6. 校验通过后说明已保存的条件、计划结构和“今天练”的下一步用法。

训练结构必须来自本次用户条件。全身 A/B 只是可能方案，不能视为所有用户的默认方案。没有可靠 GIF 映射的动作保留文字卡，不使用近似动作冒充。

`user-data/` 已包含有效档案或训练记录时，不运行初始化脚本，不覆盖任何数据。只有用户明确要求重新初始化时，才说明 `--force` 会永久删除现有记录并建议先备份。
```

- [ ] **Step 2: 更新 `AGENTS.md` 的前置判断**

把个人文件读取规则改为：

```markdown
- 处理健身请求前完整读取仓库根目录的 `SKILL.md`；先判断 `user-data/` 是否已初始化，再按 Skill 进入初始化或日常教练流程。
- 只有在已初始化时，制定或调整训练前才读取 `user-data/PROFILE.md`、`user-data/CURRENT-STATE.json`、`user-data/CURRENT-PLAN.md` 和相关近期训练记录。
```

- [ ] **Step 3: 在 README 开头增加第一次使用**

在简介后加入：

```markdown
## 第一次使用

1. Fork 或下载本仓库；
2. 在支持项目文件操作的 AI 工具中打开仓库目录；
3. 对 AI 说：`初始化健身教练`；
4. 回答目标、经验、器械、频率、时长和动作限制；
5. 初始化完成后说：`今天练`。

仓库不附带作者的个人训练计划。AI 会为当前用户生成本地计划，`user-data/` 和当前 GIF 训练卡均不会提交到 Git。
```

删除 README 中把全身 A/B 和固定动作描述为默认训练结构的章节；如需保留，标题必须改成“计划示例”，并明确不会复制给新用户。优先删除，避免双重信息。

- [ ] **Step 4: 文本一致性检查**

Run:

```powershell
rg -n "默认使用计划中的全身 A/B|默认采用全身 A/B|坐姿推胸|坐姿划船" SKILL.md README.md assets/starter-profile/CURRENT-PLAN.md
```

Expected: 不再出现默认继承个人处方的表述；动作名只允许出现在明确标注的示例或 GIF 映射说明中。

- [ ] **Step 5: 提交手动初始化流程**

```powershell
git add -- SKILL.md AGENTS.md README.md
git commit -m "feat: add conversational fitness onboarding"
```

### Task 4: 增加 GIF 素材与定制入口

**Files:**
- Create: `references/exercise-gif-customization.md`
- Modify: `extensions/exercise-visualizer/index.html`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 创建 GIF 定制说明**

文档包含以下可直接执行的示例：

```markdown
# 动作 GIF 定制

素材来自 [ExerciseGymGifsDB](https://github.com/JahelCuadrado/ExerciseGymGifsDB)。本仓库固定使用 `v1.1.0`：

`https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/api/en/exercises`

例如动作 ID `pectorals/lever-chest-press` 对应：

`https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/api/en/exercises/pectorals/lever-chest-press.json`

确认返回内容中的 `id` 与动作 ID 一致，并且存在 `gifUrl`，再把中文动作名加入 `exercise-map.js`：

```javascript
"坐姿推胸": {
  status: "resolved",
  canonicalId: "pectorals/lever-chest-press",
  instructionsZh: [
    "调整座椅，使把手大致位于胸部中段。",
    "肩胛保持稳定，沿器械轨迹推起并控制回程。"
  ]
}
```

找不到完全一致的动作时使用：

```javascript
"动作名称": {
  status: "unresolved",
  note: "尚未找到准确 GIF，保留文字训练卡"
}
```

不要用相似动作冒充。远程 GIF 或网络不可用时，训练处方仍以文字显示。素材权利和许可以素材仓库说明为准。
```

- [ ] **Step 2: 修改可视化页面的未初始化状态**

在读取数据后先判断：

```javascript
if (!map || !workout || workout.initialized === false || !Array.isArray(workout.exercises) || workout.exercises.length === 0) {
  grid.innerHTML = '<p class="fatal">尚未生成个人训练卡。请先在项目中对 AI 说“初始化健身教练”。</p>';
  status.textContent = "等待初始化";
  document.getElementById("workout-title").textContent = "请先初始化健身教练";
  return;
}
```

把脚本加载错误文字改为同时提示 `current-workout.js` 会在初始化后生成。页脚增加指向 `../../references/exercise-gif-customization.md` 的说明文字；由于本地 Markdown 链接不一定由浏览器渲染，只把它作为可复制的仓库路径展示。

- [ ] **Step 3: 从 README 链接定制说明并更新 CHANGELOG**

README 的 GIF 章节加入：

```markdown
需要为自己的计划增加或替换动作时，请看 [`references/exercise-gif-customization.md`](references/exercise-gif-customization.md)。其中包含素材仓库、固定版本接口、动作 ID 查找、中文映射和验证方法。
```

CHANGELOG 的 `Unreleased` 记录：中性初始化、个性化训练卡忽略提交、GIF 定制文档。

- [ ] **Step 4: 验证 JavaScript 与素材示例**

Run:

```powershell
node --check extensions/exercise-visualizer/current-workout.example.js
node --check extensions/exercise-visualizer/exercise-map.js
```

再请求定制文档中的示例 JSON，确认 HTTP 200、`id` 匹配且存在 `gifUrl`。

Expected: 两个语法检查退出码为 0；示例 JSON 满足三个条件。

- [ ] **Step 5: 提交 GIF 定制入口**

```powershell
git add -- README.md CHANGELOG.md references/exercise-gif-customization.md extensions/exercise-visualizer/index.html
git commit -m "docs: add exercise GIF customization guide"
```

### Task 5: 完整回归、隐私检查与发布

**Files:**
- Test: `scripts/test_regression.py`
- Verify: repository working tree and GitHub fork

- [ ] **Step 1: 在独立临时目录运行完整测试**

先创建一个明确的临时目录，并将其绝对路径设置为 `FITNESS_COACH_DATA_DIR` 和 `FITNESS_COACH_VISUALIZER_DIR`。运行：

```powershell
python scripts/test_regression.py
```

Expected: 所有测试 PASS，真实 `user-data/` 未改变。

- [ ] **Step 2: 检查公开内容不含个人计划或敏感信息**

Run:

```powershell
git ls-files user-data extensions/exercise-visualizer/current-workout.js
rg -n -i "api[_-]?key|access[_-]?token|password|authorization:" --glob '!user-data/**' .
```

Expected: 第一条没有输出；第二条没有真实凭证命中。

- [ ] **Step 3: 检查差异和工作区**

Run:

```powershell
git diff --check origin/master..HEAD
git status --short --branch
git log --oneline origin/master..HEAD
```

Expected: 无空白错误、无未提交文件，日志只包含本功能及其设计/计划提交。

- [ ] **Step 4: 推送到公开 Fork**

```powershell
git push origin master
```

- [ ] **Step 5: 验证远程发布内容**

确认 `HuaiJinHJ/fitness-coach-rpg` 的 `master` 与本地 HEAD 一致；远程存在 `current-workout.example.js` 和 GIF 定制说明，不存在 `user-data/` 与 `current-workout.js`。
