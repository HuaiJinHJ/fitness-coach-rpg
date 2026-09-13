(function () {
  "use strict";

  window.CURRENT_WORKOUT = Object.freeze({
    schemaVersion: "1.0",
    source: "user-data/CURRENT-PLAN.md",
    planLabel: "下一次",
    name: "全身 A",
    status: "待状态恢复",
    prescription: {
      sets: 2,
      reps: "8–12",
      rpe: "6–7"
    },
    notes: [
      "热身 5–8 分钟",
      "每个动作先用很轻重量练 1 组熟悉轨迹",
      "选择还能再做约 3–4 次的重量",
      "动作保持无痛、稳定、可控"
    ],
    exercises: [
      { name: "坐姿推胸", order: 1 },
      { name: "坐姿划船", order: 2 },
      { name: "哑铃罗马尼亚硬拉", order: 3 },
      { name: "腿举", order: 4 }
    ]
  });
})();
