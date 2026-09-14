# Fitness Coach — 纯教练模式

这是一个本地文件驱动的长期健身教练工作区，基于开源项目 Fitness Coach RPG 简化而来。当前只保留训练计划、训练记录、恢复判断和动态调整，不启用 RPG 或具名教练模仿。

它不是需要部署的应用，也不需要注册平台。训练事实保存在本地 JSON 和 Markdown 文件中，AI 负责读取这些事实、生成本次训练并解释调整依据。

## 第一次使用

1. Fork 或下载本仓库；
2. 在支持项目文件操作的 AI 工具中，把 `fitness-coach-rpg` 本身作为项目根目录打开；
3. 对 AI 说：`初始化健身教练`；
4. 回答目标、经验、器械、频率、时长和动作限制；
5. 初始化完成后说：`开始训练`。

仓库不附带作者的个人训练计划。个人档案、训练记录和当前 Active Workout 均不会提交到 Git。

## 两类对话

- **规划对话**：调整目标、频率、动作和阶段计划，最终把决定写回 `user-data/PROFILE.md`、`user-data/CURRENT-PLAN.md` 等长期文件。
- **训练对话**：每次都可以新建。输入 `开始训练`，AI 会从项目文件恢复状态，生成今天这一场 Active Workout，并在系统默认浏览器打开训练页。

项目文件是长期存档，对话只是操作入口；不需要维护一个永远续聊的训练线程。

## 当前目标

- 帮助用户开始并长期坚持规律训练；
- 每次去健身房前明确知道当天练什么；
- 记录动作、重量、次数、组数、RPE 或 RIR、疼痛和主观感受；
- 根据可比较的历史表现调整下一次训练；
- 中断、疲劳、疼痛或停滞时主动降级，而不是机械执行。

首个训练周期通常以出勤、动作学习和建立基线为主；具体频率和训练结构由初始化结果决定。

## 日常使用

正常情况下，在项目中直接对 AI 说：

```text
开始训练
```

AI 会读取个人档案、当前状态、长期计划和必要的历史摘要，生成今天这一场 Active Workout。默认不会固定询问睡眠、精神状态和疼痛；只有用户主动报告异常、但信息不足以安全调整时，才补问最少必要信息。

正常交互示例：

```text
用户：开始训练。
教练：今天是全身 A，训练页已在默认浏览器打开。正常训练不用回这里；器械占用、重量不合适或身体不适时再告诉我。
```

如果你已经知道今天状态不同，可以直接一次说完：

```text
开始训练，昨晚 6.5 小时，精神一般，无痛。
```

AI 会直接把这些信息纳入本次训练，不重复追问。

训练中正常执行即可。遇到器械占用、重量不合适、动作不熟、异常疲劳或疼痛时，再随时反馈。

训练后可以自然语言汇报。以下动作和重量只用于示范记录方式，不代表默认计划：

```text
坐姿推胸热身 10 公斤 12 次，正式组 20 公斤 12 次和 11 次，最后一组 RPE 7。
坐姿划船 25 公斤两组，各 10 次，右手有点先累。
腿举没做，器械一直有人。总共 42 分钟，整体 RPE 7，没有疼痛。
```

AI 会将已知信息整理为结构化记录。没有提供的字段保持为空，不会被编造。

## Active Workout 与动作可视化

`user-data/CURRENT-PLAN.md` 保存长期训练模板；`extensions/exercise-visualizer/current-workout.js` 保存“今天这一场”的 Active Workout 快照。两者不是同一个对象。

当你说 `开始训练` 后，AI 会：

1. 读取长期计划和历史表现；
2. 如有必要，根据你主动报告的当天状态调整本次处方；
3. 生成 `current-workout.js`；
4. 运行 `python scripts/validate_workout.py --session-id <本次 sessionId>` 校验本次训练；
5. 运行 `python scripts/open_workout.py --session-id <本次 sessionId>`，用系统默认浏览器打开训练页。

临时降组数、降强度或替换动作默认只作用于本次 Active Workout，不修改长期计划。

`extensions/exercise-visualizer/` 是训练执行展示层：

- `exercise-map.js`：保存当前动作与 ExerciseGymGifsDB canonical ID 的映射；
- `current-workout.example.js`：公开的空白格式示例；真正的 `current-workout.js` 由 AI 在每次开始训练时生成并被 Git 忽略；
- `index.html`：展示本次训练处方，并从固定版本 `v1.1.0` 获取 GIF、主要肌群、器械和动作说明；
- `scripts/open_workout.py`：交给操作系统默认浏览器打开训练页，而不是让 Codex 把 HTML 当源码打开。

网络或 CDN 不可用时，页面自动保留文字训练卡。没有可靠 GIF 映射的动作也会保留完整文字处方，不使用近似动作冒充。

需要增加或替换动作时，请看 [`references/exercise-gif-customization.md`](references/exercise-gif-customization.md)。

## 动态调整

- 两个正式组都达到 12 次，动作稳定、无疼痛，且强度不高于 RPE 8：下次最小幅度加重；
- 完成 8–11 次：保持重量，优先增加次数；
- 未达到 8 次或强度达到 RPE 9：降低约 5%–10%；
- 停练 7–14 天：参考重量降低约 10%；
- 停练 15–30 天：参考重量降低约 20%；
- 停练超过 30 天：重新建立基线；
- 连续三次停滞：检查技术、组间休息、恢复和动作适配；
- 连续两次最高工作重量下降超过 10%：安排减量训练。

脚本负责保存、校验、汇总和产生规则化建议；最终训练计划仍由 AI 结合用户当天状态解释和应用。

## 数据文件

- `user-data/PROFILE.md`：长期稳定的个人资料；
- `user-data/CURRENT-PLAN.md`：当前阶段长期训练结构和衔接规则；
- `user-data/CURRENT-STATE.json`：恢复状态、近期可比表现和下一次建议；
- `user-data/sessions/YYYY-MM-DD.json`：逐次训练事实，只追加不覆盖；
- `extensions/exercise-visualizer/current-workout.js`：当前 Active Workout 快照；
- `SKILL.md`：教练行为说明；
- `AGENTS.md`：确保新任务自动进入纯教练流程。

持久连续性来自这些本地文件，而不是聊天窗口本身。`user-data/` 和当前训练卡均被 Git 忽略。

## 脚本

项目使用 Python 3.8+ 标准库，无第三方依赖。

```text
python scripts/init_profile.py --name 你的名字
python scripts/validate_onboarding.py
python scripts/validate_workout.py --session-id <本次 sessionId>
python scripts/open_workout.py --session-id <本次 sessionId>
python scripts/append_session.py --file session.json
python scripts/update_summary.py
python scripts/validate_state.py
python scripts/test_regression.py
```

自动测试必须使用临时数据目录，不能接触真实 `user-data`。当前测试入口已经内置隔离机制。

## 安全边界

训练中出现锐痛、关节不稳、明显肿胀或疼痛持续加重时，停止相关训练。AI 不诊断疾病，也不替代医生或康复专业人员。

## 来源与许可

本工作区基于 [chenklein26-maker/fitness-coach-rpg](https://github.com/chenklein26-maker/fitness-coach-rpg) 调整。原项目与本工作区均使用 MIT License，详见 `LICENSE`。

动作元数据和远程 GIF 来自 [ExerciseGymGifsDB](https://github.com/JahelCuadrado/ExerciseGymGifsDB)，固定使用 `v1.1.0`。本仓库不复制 GIF 文件；GIF 权利归各自权利人所有。
