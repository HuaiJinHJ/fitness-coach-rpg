(function () {
  "use strict";

  window.EXERCISE_MAP = Object.freeze({
    schemaVersion: "1.0",
    source: {
      name: "ExerciseGymGifsDB",
      version: "v1.1.0",
      repository: "https://github.com/JahelCuadrado/ExerciseGymGifsDB",
      apiBase: "https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/api/en/exercises"
    },
    displayNames: {
      muscles: {
        abductors: "髋外展肌",
        abs: "腹肌",
        abdominals: "腹肌",
        adductors: "髋内收肌",
        biceps: "肱二头肌",
        calves: "小腿肌群",
        cardio: "心肺",
        delts: "三角肌",
        shoulders: "肩部",
        forearms: "前臂",
        glutes: "臀肌",
        hamstrings: "腘绳肌",
        lats: "背阔肌",
        "levator-scapulae": "肩胛提肌",
        "lower-back": "下背部",
        pectorals: "胸肌",
        quads: "股四头肌",
        "serratus-anterior": "前锯肌",
        spine: "脊柱肌群",
        traps: "斜方肌",
        triceps: "肱三头肌",
        "upper-back": "上背部"
      },
      equipment: {
        band: "弹力带",
        "resistance band": "弹力带",
        barbell: "杠铃",
        bodyweight: "自重",
        "body weight": "自重",
        cable: "绳索器械",
        dumbbell: "哑铃",
        "ez-bar": "曲杆杠铃",
        kettlebell: "壶铃",
        lever: "固定器械",
        machine: "器械",
        other: "其他",
        sled: "倒蹬 / 雪橇式器械",
        smith: "史密斯机",
        "smith machine": "史密斯机"
      }
    },
    exercises: {
      "坐姿推胸": {
        status: "resolved",
        canonicalId: "pectorals/lever-chest-press",
        instructionsZh: [
          "调整座椅，使把手大致位于胸部中段，背部贴稳靠垫。",
          "双脚踩稳，肩胛骨向后下方保持稳定，手腕与前臂自然对齐。",
          "沿器械轨迹向前推至手臂接近伸直，不要锁死肘关节。",
          "缓慢屈肘回到起点，全程保持胸部发力并控制重量。"
        ]
      },
      "坐姿划船": {
        status: "resolved",
        canonicalId: "upper-back/lever-seated-row",
        instructionsZh: [
          "调整座椅和胸垫位置，坐稳；如有胸垫，让胸口自然贴靠。",
          "保持脊柱中立、肩膀下沉，先稳定肩胛骨再开始拉动。",
          "肘部向身体后方移动，在末端轻轻收紧肩胛骨。",
          "控制把手回到起点，避免耸肩或借身体后仰甩动。"
        ]
      },
      "哑铃罗马尼亚硬拉": {
        status: "resolved",
        canonicalId: "glutes/dumbbell-romanian-deadlift",
        instructionsZh: [
          "双脚约与髋同宽，双手持哑铃，膝盖保持轻微弯曲。",
          "保持背部中立，将髋部向后推，哑铃贴近腿部向下移动。",
          "下降到腘绳肌有明显拉伸、同时背部仍能稳定的位置，不必追求触地。",
          "脚掌踩稳并伸髋站起，顶端收紧臀部，不要用下背部过度后仰。"
        ]
      },
      "腿举": {
        status: "resolved",
        canonicalId: "glutes/sled-45-leg-press",
        instructionsZh: [
          "背部和臀部贴稳靠垫，双脚在踏板上站稳，间距约与肩同宽。",
          "解除安全装置后缓慢屈膝下放，膝盖方向与脚尖保持一致。",
          "只下降到腰背仍贴稳且膝盖无痛的范围，不要让骨盆卷起。",
          "脚掌均匀发力推回，接近顶端时不要锁死膝关节。"
        ]
      },
      "高位下拉": {
        status: "unresolved",
        note: "待确认握法与器械变式"
      },
      "上斜器械推胸": {
        status: "resolved",
        canonicalId: "pectorals/lever-incline-chest-press",
        instructionsZh: [
          "调整座椅，使把手大致位于上胸位置，头部和背部贴稳靠垫。",
          "双脚踩稳，肩胛骨向后下方保持稳定，避免耸肩。",
          "沿器械轨迹向前上方推至手臂接近伸直，不要锁死肘关节。",
          "缓慢回到起点，肘部不过度外展；肩部不适时缩小活动范围或停止。"
        ]
      },
      "臀推/臀桥": {
        status: "unresolved",
        note: "二选一动作，待训练当天确认"
      },
      "低台阶上台或腿举": {
        status: "unresolved",
        note: "二选一动作，待训练当天确认"
      },
      "游泳 / 恢复": {
        status: "unresolved",
        note: "恢复活动不匹配力量训练 GIF"
      }
    }
  });
})();
