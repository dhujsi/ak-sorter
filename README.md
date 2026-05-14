# ak-sorter — 明日方舟已实装干员喜好排序

基于 [Khrisma13/barank](https://github.com/Khrisma13/barank) 的二选一排序创意改造的明日方舟干员喜好排序工具。本项目代码位于 [dhujsi/ak-sorter](https://github.com/dhujsi/ak-sorter)。

## 功能

- **二选一排序**：通过锦标赛式两两对比，确定你的干员喜好排名
- **星级筛选**：按 1-6 星筛选参与排序的干员范围
- **排名数量选择**：Top 10 / 20 / 30 / 50 / 100 / 全选
- **Tier 图生成**：基于排序结果自动生成 10 档 Tier 图，支持拖拽微调
- **图片导出**：支持导出排名图（半身图）和 Tier 图（头像），附带当前页二维码

## 使用方法

直接用浏览器打开 `index.html`，或部署到任意静态服务器。

## 本地运行

```bash
# Python
python -m http.server 8080

# Node.js
npx serve .
```

## 资源来源

- 干员数据和头像来自 [yuanyan3060/ArknightsGameResource](https://github.com/yuanyan3060/ArknightsGameResource)
- 干员半身图来自 [PRTS Wiki](https://prts.wiki/)
- 游戏素材（角色形象、名称、设定等）版权归鹰角网络（Hypergryph）所有

## 许可

- 本项目代码基于 [MIT License](LICENSE) 授权
- MIT 不适用于游戏素材（头像、半身图、角色名称等），这些内容的版权归原权利方所有
- 原项目：https://github.com/Khrisma13/barank

## 声明

本站是非官方 fan-made 项目，与鹰角网络、Yostar 无关。
