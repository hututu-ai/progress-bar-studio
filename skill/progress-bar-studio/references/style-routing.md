# 样式路由与保守迁移

`scripts/style_router.py` 将两套实现并存，保留真实几何和各自的配置单位。原来的
`render_progress.py` 仍按候选经典 S1–S7 的明确契约工作；跨来源选择必须走路由器。
不按同名编号合并实现，不从安装目录读取默认 profile，不自动复制任何角色或视频。

## 稳定键

0.7.4 新项目统一通过 `assets/selected-styles.json` 和 `style_router.py new-config` 取当前默认值。
01/02 为 readable-20261030，07 为 editorial-20261030，08 为 readable-20261030，
其他四款维持各自定义；不再把 refined-20261030 当作通用新建配置版本。
旧文档下方对 refined/legacy 的描述只用于复现旧项目，不覆盖当前清单。

新建示例（路径、配色、字体与角色 JSON 由 Agent 按当前项目填写）：

```text
python scripts/style_router.py new-config 项目/路由.json --option 07 --timeline 当前章节.json --font-regular 本机常规字体 --font-bold 本机粗体字体 --width 2160 --palette 已选配色.json
```

有 IP 时加 `--character 四帧配置.json`，使用对应引擎的字段并指向当前项目实际素材。
新建检查 3–5 章；原生、迁移及旧项目读取不强制改旧章数。
图册和演示同取当前清单；完整复用方案见 visual-profiles.md，旧 schema-4 手动适配另保留。

当前新项目精选图册只展示 01、02、07、08、10、11、13、15，共八款，
保留原图号，不顺延重编号。03、05、06、09 已退出新项目选择；14 与 11 近似，
12 与 11 近似、04 与 10 同属横向色带，因此从展示收起。底层实现保留供旧项目
继续读取，不能主动重新推荐已撤下款式。E–H 试做不进入目录，也不增加额外选择入口。
`catalog --creator-facing` 输出这八款；不带参数的 catalog 是完整技术兼容列表。

### 当前改款与旧配置隔离

07 本轮预览另用 `visualRevision: "editorial-20261030"`，用户可见名为「细轨章节导航」。
采用一条连续轨道、完整编号章名和当前序号的小色块；不再画旗签或悬挂短线。
所有章名固定保留，当前 / 已讲 / 未讲分态；终点全部为已讲。
有 IP 时脚点仍绑定同一轨道填充端点，无 IP 时回收角色空间。
该字段仅适用于 classic:S7。旧 legacy / refined-20261030 的像素逻辑保留，
不能把本次待用户审阅的外观静默改到旧成品上。

新 rendererConfig 指定 `visualRevision: "refined-20261030"`：
01 等宽单层胶囊、三态底色、较大章名；02 保持真实时长分段，增加小序号与较大章名；
旧 refined 的 07 只保留一条上方进度／行走轨道，章节签用短线挂在轨道下方；当前新建 07 已改用前述 editorial 版本。15 只保留 21 个细点、
当前位置和一行章名，去掉序号、状态行、大胶囊与定位圈。11 保留简洁短横线，
当前章名用深字，不再把浅青柠直接当小字颜色。

经典配置可传 `fontBold`，与 `font` 一样相对配置文件解析；只用于本次改款的主标题。
未指定改款字段时旧像素逻辑保持原样。新旧预设复用时显式保留该字段与字体，不能
把新图册预览和旧配置的 MOV 混用；PNG 和 MOV 仍由同一个渲染器生成。

| 稳定键 | 原实现编号 | 样式 |
| --- | --- | --- |
| classic:S1 | 新 S1 | 章节胶囊 |
| classic:S2 | 新 S2 | 分段跑道 |
| classic:S3 | 新 S3 | 文字推进；细分隔与短下划线 |
| classic:S4 | 新 S4 | 更薄的标签分栏填色带 |
| classic:S5 | 新 S5 | 当前章节卡 |
| classic:S6 | 新 S6 | 角落圆环 |
| classic:S7 | 新 S7 | 当前为细轨章节导航；悬挂签仅旧版本 |
| gallery:01 | 01 / S1 | 双层胶囊 |
| gallery:02 | 02 / R1 | 浮标气泡 |
| gallery:03 | 03 / R2 | 贯穿章节带 |
| gallery:04 | 04 / R3 | 短横线分段 |
| gallery:05 | 05 / R4 | 细线节点 |
| gallery:06 | 06 / R5 | 箭头阶梯 |
| gallery:07 | 07 / R6 | 渐变分段 |
| gallery:08 | 08 / R7 | 点阵进度 |

另保留 `legacy:S1`、`legacy:S2`、`legacy:S3`、`legacy:S5`、`legacy:S6`、
`legacy:S7`、`legacy:S8`、`legacy:S9` 八个历史键。其中旧 S5 是里程碑圆点、
旧 S6 是章节卡片、旧 S7 是书签页签，始终不重解释为新 S5/S6/S7。旧 S4 没有
安装版渲染实现，不能自动映射；原仓库来源的经典 S4 应明确选择 `classic:S4`。
`custom` 仍是单独的设计路线，不冒充内置样式。

普通 catalog 输出八旧加七新的 15 项；加 `--include-legacy` 后输出 23 个稳定键。
来源不明的 `S1`、`S5`、`01` 或 `R1` 全部拒绝。明确的来源标识为
`installed-20260922` 或 `classic-0.5`。稳定键与内部 style、来源记录冲突时也拒绝。

## 路由配置

外层固定 `schemaVersion: 1`，但它与另外两套原生 schema 1 不是同一种格式。
必须同时检查 `styleKey` 和 `rendererConfig`，不能只看版本数字。

```json
{
  "schemaVersion": 1,
  "styleKey": "gallery:04",
  "assetBase": ".",
  "rendererConfig": {
    "style": "04",
    "outputWidth": 2160,
    "displayWidth": 480,
    "fontRegular": "fonts/regular.otf",
    "fontBold": "fonts/bold.otf",
    "labelSize": 18,
    "kickerSize": 11,
    "progressMode": "chapter-weighted",
    "character": {"mode": "none"},
    "palette": {
      "surface": "#FFFFFF", "active": "#19766C", "inactive": "#DDECEA",
      "pill": "#EEF6F4", "text": "#183D39", "quiet": "#56736F",
      "outline": "#BCD8D2", "selected": "#176558", "onSelected": "#FFFFFF"
    }
  },
  "timeline": {
    "duration": 10,
    "fps": 24,
    "chapters": [
      {"start": 0, "label": "开场", "kicker": "开场"},
      {"start": 3, "label": "安装", "kicker": "第一步"},
      {"start": 7, "label": "验证", "kicker": "第二步"}
    ]
  },
  "synthetic": true
}
```

上例只是合成结构示意，字体是需用户环境填入的占位路径，青绿色是显式示例，
不是全局默认。真实制作必须换成当前视频时间线、实际字体与获批配色。

`classic:*` 的 rendererConfig 使用 [rendering.md](rendering.md) 的完整配置，
duration/fps/chapters 留在其内部，不另传外层 timeline。两套字体、字级、角色高度、
配色字段和进度映射都不互转；因此旧 2160 宽不会因“2K”标签变成 2560，
旧 chapter-weighted 不会静默转成 time-linear。
图库 timeline 的 fps 同时接受有限数值和旧 source.json 的分数字符串
（例如 `30000/1001`）；原始字符串保留在迁移配置里，不按整数帧率改写。

`assetBase` 相对路由文件所在目录解释。迁移到新文件夹时，迁移器记录相对的原
配置目录，使原字体/角色路径继续指向同一文件，不复制或改写那些资产。
配置和迁移输出可能含私有引用，必须留在私人项目中，不能打入公共包。

## 命令

```bash
python3 scripts/style_router.py catalog
python3 scripts/style_router.py catalog --include-legacy
python3 scripts/style_router.py migrate-config /private/old-render.json /private/new/routed.json \
  --origin installed-20260922 --timeline /private/current-timeline.json
python3 scripts/style_router.py inspect /private/new/routed.json
python3 scripts/style_router.py validate /private/new/routed.json
python3 scripts/style_router.py preview /private/new/routed.json /private/preview.png --time 3
python3 scripts/style_router.py mov /private/new/routed.json /private/debug.mov \
  --purpose debug --start 2.5 --seconds 1
```

所有输出拒绝覆盖已有文件。inspect 检查输入存在性并报告缺失项，不等于布局、
透明素材、视觉批准或编辑器验收；validate 才构造渲染器检查布局。PNG 和 MOV
使用同一分派。MOV 走候选编码器的真实帧时间，不沿用旧 CLI 将末帧强推到终点的行为。
无音轨、ProRes 4444、Alpha、原子不覆盖规则保持一致，仍须全量 Alpha 扫描。

sample 最长 15 秒，debug 最长 30 秒。final 必须明确传 `--final-approved`，
使用完整时间线且不是 synthetic/demoLabel 配置；该标记依然只是操作者对真实授权的
陈述，不会产生用户授权。旧配置或 profile 的 approvedAt 等字段绝不自动当作新视频批准。

## 可以迁移与必须人工复核的边界

- 已知来源、字段可完整表示的旧 render config 可以包入新路由格式；原字级、
  尺寸、进度模式、角色帧顺序、脚点、配色与章节证据字段均保留。
- 明确从旧安装版导入、但配色 token 缺失时，捕获旧实现当时的有效 token，
  并在 provenance.expandedLegacyPaletteTokens 逐项列出；这只冻结旧外观，
  不批准本次视频配色，也不设定任何以后项目的默认色。
- 历史 profile 的 style 是对象，通常缺少当前时间线、可执行的具体变体、逐帧
  脚点或字体文件；inspect 只给人工复核报告，migrate-config 返回 2 且不写迁移文件。
- 未知字段、未知 token、不存在的旧 S4、编号/来源冲突、none 模式暗藏角色字段
  都不能静默删掉或猜测。缺文件在 inspect 报告，并阻止实际渲染。
- 不把旧 schema 1 升成 verified 品牌预设，不复制 approvedAt，不生成假样片批准，
  不继承旧视频章节或时长。品牌预设 schema 4 的自动导入仍未实现。
- schema 4 保存器仍只接受经典 S1–S7 和 custom，不能保存 gallery/legacy 稳定键。
  图库复用应先保留私有项目中的路由配置；不能把 gallery:06 改名 S6 骗过保存器。
- 时间线由本次项目提供；即使恰巧用了旧的时间线文件，工具也不能替代 sourceId、
  哈希与语义证据核验。真正渲染前仍按 Skill 的当前源视频工作流进行。

回归测试使用独立临时配置和合成角色，对八旧预设及历史 S 样式比较迁移前后像素；
新七样式比较原生与路由结果。用户真实 profile 的检查结果只保留脱敏摘要，
不随公共包交付。没有真实成片和剪映操作，不能声称最终兼容性已通过。
