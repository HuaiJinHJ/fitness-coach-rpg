# Fitness Coach Workspace

- 面向用户使用简体中文，先给当天行动，再给必要理由。
- 处理健身请求前完整读取仓库根目录的 `SKILL.md`，并遵循其中的纯教练流程。
- 制定或调整训练前，读取 `user-data/PROFILE.md`、`user-data/CURRENT-STATE.json`、`user-data/CURRENT-PLAN.md` 和相关近期训练记录。
- RPG、剧情、等级、经验值、属性和具名教练模仿均处于停用状态。
- 用户未提供的训练数据保持为空，不猜测或补写。
- 训练记录只追加，不覆盖已有动作；每次调整都说明所依据的历史表现或当日状态。
- 任何自动测试都必须通过 `FITNESS_COACH_DATA_DIR` 指向临时目录，禁止测试读写真实 `user-data`。
