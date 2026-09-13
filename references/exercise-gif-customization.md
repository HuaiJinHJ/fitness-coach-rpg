# 动作 GIF 定制

动作素材来自 [ExerciseGymGifsDB](https://github.com/JahelCuadrado/ExerciseGymGifsDB)。本仓库固定使用 `v1.1.0`，避免上游文件变化导致已经配置的动作突然失效。

## 素材接口

接口基址：

```text
https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/api/en/exercises
```

动作的 canonical ID 由“主要肌群目录/动作文件名”组成。例如：

```text
pectorals/lever-chest-press
```

对应的动作信息地址是：

```text
https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/api/en/exercises/pectorals/lever-chest-press.json
```

在浏览器打开地址，确认返回内容中的 `id` 与 canonical ID 完全一致，并且存在 `gifUrl`，再加入本仓库映射。

## 添加中文动作映射

编辑 `extensions/exercise-visualizer/exercise-map.js`，在 `exercises` 中加入中文动作名：

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

中文动作名必须和本地 `current-workout.js` 中的动作名一致。`instructionsZh` 应描述同一个动作和器械变式，不要把其他动作的说明挪用过来。

如果还没有找到完全一致的素材，保留文字训练卡：

```javascript
"动作名称": {
  status: "unresolved",
  note: "尚未找到准确 GIF，保留文字训练卡"
}
```

不要用相似动作冒充。远程 GIF、素材接口或网络不可用时，训练处方仍会以文字显示。

## 验证

修改后先检查 JavaScript 语法：

```text
node --check extensions/exercise-visualizer/exercise-map.js
```

然后重新打开 `extensions/exercise-visualizer/index.html`，确认动作名称、器械、主要肌群、中文提示和 GIF 都对应同一动作。

## 数据与许可

本仓库只保存动作 ID 和远程链接，不复制整套 GIF 文件。GIF 和动作元数据的权利及许可，以 [ExerciseGymGifsDB](https://github.com/JahelCuadrado/ExerciseGymGifsDB) 的说明为准。
