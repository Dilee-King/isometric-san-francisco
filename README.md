# Isometric San Francisco

旧金山市区与海湾沿岸的精细等轴测地图，计划加入车、船、飞机，以及可以独立组合的日夜与天气变化。

An illustrated isometric San Francisco, with a living waterfront, moving traffic, and changing light and weather.

**当前状态：方案与仓库初始化。尚未发布地图应用，也没有完成全市图块。**

## 方向

沿用 [Isometric NYC](https://cannoneyed.com/projects/isometric-nyc) 与 [Isometric Vancouver](https://vancouver.isoworld.xyz/) 的公开制作思路：统一正交相机、真实城市结构参照、逐块绘制与接缝修整、多级图块浏览。浏览体验采用固定斜视角，支持平移和缩放。

首期目标是旧金山市区及北部、东部海湾沿岸。制作从 Ferry Building、Financial District 与 Embarcadero 的连续样区开始，再逐块向相邻市区、北部滨水、SoMa 与 Mission Bay 扩展。这个制作顺序是当前提案；完整边界由覆盖清单记录。

| 组成 | 目标行为 | 当前状态 |
| --- | --- | --- |
| 城市地图 | 细密建筑、街道、山坡、码头与岸线，连续缩放浏览 | 设计完成，未实现 |
| 车辆 | 按道路、方向、车道和信号组织的示意交通 | 已定义要求，未实现 |
| 船舶 | 航道、码头停靠、慢速货船与渡轮尾流 | 已定义要求，未实现 |
| 飞机 | 与固定地图坐标配准的偶发飞越 | 已定义要求，未实现 |
| 日夜 | 配准的昼暮夜图层、窗灯、路灯与交通灯光 | 已定义要求，未实现 |
| 天气 | 晴、多云、海雾、雨，独立于时间组合 | 已定义要求，未实现 |

首期不含 SFO 机场地面，飞机先表现为空中飞越。交通与天气是可控的演示动画；接入实时数据属于独立的后续工作。

## 技术路线

离线制作统一相机下的精绘图块，浏览器加载二维图块与动态叠加层。以纽约公开的 React / TypeScript / Vite / OpenSeadragon / DZI 流程为首版基础，参考温哥华的 WebGL 图层和 worker 交通组织。所有图层共用一套世界坐标到画面的变换。

昼暮夜版本和效果遮罩必须配准；车辆、船舶及地面灯光应接受建筑遮挡。移动太阳阴影只有在具备可重照明数据时才列为完成，单纯给整图加色不满足日夜效果的验收要求。

完整方法见 [项目设计](docs/project-design.md)、[技术参照核对](docs/reference-audit.md) 和 [视觉规范](DESIGN.md)。

## 更新方式

- [路线图](ROADMAP.md)：每个阶段的交付物与完成条件。
- [覆盖计划](data/coverage-plan.json)：计划范围与已交付范围分别记录。
- [贡献说明](CONTRIBUTING.md)：修图、路线、效果和代码的提交规则。
- [致谢](ACKNOWLEDGMENTS.md)：与纽约、温哥华及相关开源项目的联系。
- [更新记录](CHANGELOG.md)：只记录已经交付的变化。

后续每个地图版本将绑定图块清单、来源记录、坐标配置和应用提交。大型图块及原始数据采用独立版本化存储，代码仓库保留清单与可复现步骤。

## 阅读与运行

当前提交是文档版本，没有 `npm run dev`、构建产物或在线演示。后续应用交付时会在这里补充经过实际验证的安装与运行步骤。

## License

本仓库原创代码与文档采用 [MIT](LICENSE)。第三方数据、图像和代码保留各自的许可及署名；参照项目的许可不自动覆盖它们引用的外部数据。详见 [资产规则](assets/README.md)。
