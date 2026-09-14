# Fitness Coach Workspace

- 面向用户使用简体中文，先给当天行动，再给必要理由。
- 处理健身请求前完整读取仓库根目录的 `SKILL.md`；先判断 `user-data/` 是否已初始化，再按 Skill 进入初始化、规划或日常教练流程。
- “开始训练 / 今天练”等请求进入 Active Workout 流程：读取长期文件，生成本次训练，运行 `python scripts/validate_workout.py --session-id <本次 sessionId>`，再运行 `python scripts/open_workout.py --session-id <本次 sessionId>`。
- 默认不执行固定训练前三问；只在用户主动报告异常且信息不足以改变处方时补问最少必要信息。用户已经提供的状态信息不得重复追问。
- 训练页必须由系统默认浏览器打开；不要用 Codex 编辑器打开 `index.html` 代替训练页面。
- 只有在已初始化时，制定或调整训练前才读取 `user-data/PROFILE.md`、`user-data/CURRENT-STATE.json`、`user-data/CURRENT-PLAN.md` 和相关近期训练记录。
- 长期计划变更必须写回项目文件；聊天上下文不是训练事实来源。临时状态调整默认只改变本次 Active Workout。
- RPG、剧情、等级、经验值、属性和具名教练模仿均处于停用状态。
- 用户未提供的训练数据保持为空，不猜测或补写。
- 训练记录只追加，不覆盖已有动作；每次调整都说明所依据的历史表现或当日状态。
- 任何自动测试都必须通过 `FITNESS_COACH_DATA_DIR` 指向临时目录，禁止测试读写真实 `user-data`。
