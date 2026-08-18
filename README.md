# ElleFlow｜小人走路视频进度条动画

> 让你的 IP 小人沿着视频章节进度条走起来，导出可直接叠加到剪映等软件的透明动画。

## ElleFlow 是什么

做一条带小人行走效果的章节进度条，通常要自己听内容、划章节、卡时间、做动画、调关键帧。

现在，把视频交给 AI：

```text
上传视频 → 识别内容 → 自动分章 → 生成角色 → 选择样式 → 导出透明动画
```

[30 秒上手](#30-秒上手) · [最终产出](#最终产出) · [支持的-agent](#支持的-agent) · [四种样式](#四种样式) · [详细流程](#详细流程)

---

## 安装后，先这样开始

安装完成后，不需要记任何指令。先把一段带声音的视频发给 Agent，它应先告诉你这个 Skill 能做什么，并提示你可以继续发送：

- **只发视频**：先分析内容，给出章节划分；
- **视频 + 角色图**：让你的 IP 跟着进度条移动；
- **视频 + 参考图**：按喜欢的版式重建；
- **视频 + 一个颜色**：按品牌色设计。

最简单的一句话是：

```text
给这个视频做进度条。
```

首次引导不应抛出“Alpha、ProRes、五步工作台、manifest”等内部术语；这些只在用户需要确认设计或导出格式时再说明。

---

## 它做了什么

你只需要提供：

- 一段带声音的视频；
- 一张角色图（可选）；
- 一张喜欢的进度条参考图（可选）；
- 想使用的颜色（可选）。

开始时，Agent 会先和你确认两件事：

- **成品放在哪**：未指定时，默认放在源视频所在文件夹，且不会覆盖同名文件；
- **导出多清晰**：在 1080p、2K、4K 中选择。它会先根据真实视频时长和帧率估算三档文件大小，设计确认后再用短样片给出更准确的最终估算。

然后告诉 Agent：

```text
使用 progress-bar-studio 给这个视频制作章节进度条。
分析真实语音内容，使用我上传的角色生成四帧行走动画。
透明底，适配剪映，先确认章节和静态效果，再制作完整版。
```

Skill 会完成：

```text
视频检查 → 语音转写 → 语义分章 → 角色处理 → 样式配色 → 动画制作 → 透明度质检 → 导出
```

---

## 最终产出

你拿到的是一套可继续剪辑的透明素材：

| 文件 | 用途 |
| --- | --- |
| `progress_bar.mov` | 带 Alpha 通道的 ProRes 4444 透明进度条母版 |
| `preview.mp4` | 保留原视频声音的轻量叠加预览 |
| `character.png` | 处理完成的透明角色 PNG |
| `walk_01.png`–`walk_04.png` | 四帧透明行走姿势 |
| `walk.webp` | 四帧循环动画预览 |
| `chapters.json` | 章节时间、名称与边界 |
| `style.json` | 样式、配色、尺寸与确认记录 |
| `qc/` | Alpha、多背景和章节边界质检图 |

默认“4K 进度条”指 **3840 像素宽的透明条带**，高度随样式调整。

---

## 30 秒上手

### 方法一：让 Agent 帮你安装

把下面这句话发给 Codex、Claude Code、Cursor 或 GitHub Copilot：

```text
请帮我安装这个 Skill：
https://github.com/hututu-ai/progress-bar-studio

安装 skill/progress-bar-studio，并告诉我如何调用。
```

安装完成后，重新打开 Agent 或新建任务，再上传视频开始制作。

### 方法二：手动安装

先下载仓库：

```bash
git clone https://github.com/hututu-ai/progress-bar-studio.git
cd progress-bar-studio
```

再按使用的 Agent 复制 Skill：

| Agent | 全局安装命令 |
| --- | --- |
| **Codex** | `mkdir -p ~/.codex/skills && cp -R skill/progress-bar-studio ~/.codex/skills/` |
| **Claude Code** | `mkdir -p ~/.claude/skills && cp -R skill/progress-bar-studio ~/.claude/skills/` |
| **Cursor** | `mkdir -p ~/.cursor/skills && cp -R skill/progress-bar-studio ~/.cursor/skills/` |
| **GitHub Copilot** | `mkdir -p ~/.copilot/skills && cp -R skill/progress-bar-studio ~/.copilot/skills/` |

安装成功后，目标目录应为：

```text
progress-bar-studio/
├── SKILL.md
├── assets/
├── references/
└── scripts/
```

---

## Agent 与环境兼容性

本项目遵循 Agent Skills 的 `SKILL.md` 格式；能加载该格式的 Agent 才能识别工作流。是否能完成媒体制作，还取决于宿主是否允许读取本地文件、运行脚本、调用图像能力以及导入剪辑软件验证。

| Agent | 常见安装位置 | 说明 |
| --- | --- | --- |
| **Codex** | `~/.codex/skills/` 或项目级技能目录 | 需有本地媒体读取和命令执行能力。 |
| **Claude Code** | `~/.claude/skills/` 或插件安装目录 | 需确认本机能运行媒体脚本。 |
| **Cursor** | `.cursor/skills/` 或 `.agents/skills/` | 以 Cursor 当前 Skills 文档为准。 |
| **GitHub Copilot** | `.github/skills/` 或 `.agents/skills/` | 以 Copilot 当前 Agent Skills 文档为准。 |

安装不等于媒体链路已验证。开始处理任何视频前，先运行：

```bash
python3 skill/progress-bar-studio/scripts/preflight.py \
  --source-video /path/to/video.mp4 \
  --output-dir /path/to/output \
  --json
```

它会检查 `ffmpeg`、`ffprobe`、ProRes 4444 编码器、Pillow、目标文件夹可写性和可用磁盘；没有音频时会要求你补一份可编辑的章节时间表，或换用带声音的版本。转写、图像编辑和剪映/PR 导入测试仍取决于正在使用的 Agent 与本机软件。

---

## 直接这样用

### 四帧行走角色

```text
使用 progress-bar-studio 处理这个视频。
根据语音内容自动划分章节，把我上传的角色处理成四帧逐帧行走版本。
使用 S1 章节胶囊，主色 #E89AB3，透明底，导出 ProRes 4444 MOV。
```

### 单张轻动角色

```text
给这个视频制作章节进度条。
角色使用单张轻动模式，选择 S2 分段跑道。
先给我章节时间轴和静态叠加效果，确认后再制作完整版。
```

### 纯进度条

```text
分析这个视频的章节，使用 S3 文字推进样式。
不使用角色，使用粉色系，导出 3840 像素宽的透明 MOV。
```

### 参考图定制

```text
使用我上传的进度条参考图进行自定义重建。
提取它的轨道、节点、标签层级和进度填充方式，替换为本视频章节与我的角色。
配色改为 #E89AB3，先确认结构拆解和静态预览，再导出透明完整版。
```

![参考图定制流程](docs/images/custom-reference.png)

---

## 角色模式

| 模式 | 适合什么情况 | 输出 |
| --- | --- | --- |
| **不使用角色** | 极简知识口播、画面空间较小 | 纯轨道与章节动画 |
| **单张轻动** | 已有一个合适的侧向角色，希望快速制作 | 单张透明 PNG + 位移动画 |
| **四帧行走** | 希望角色真正迈步，增强 IP 感 | 四帧 PNG + WebP 预览 + 逐帧循环 |

上传角色原图后，AI 会生成朝右行走版本，并检查角色特征、透明边缘和脚底基线。角色在进度条上的位置由所选样式自动决定。

---

## 四种样式

| 样式 | 特点 | 适用内容 |
| --- | --- | --- |
| **S1 章节胶囊** | 章节清晰，当前章节突出 | 知识讲解、课程、方法分享 |
| **S2 分段跑道** | 节奏轻快，角色沿分段前进 | 教程、游戏感内容、轻松口播 |
| **S3 文字推进** | 占用空间少，信息简洁 | 竖屏口播、字幕较多的视频 |
| **S4 标签分栏带** | 章节信息完整，角色位于当前栏 | 系列内容、步骤型教程 |

![四种进度条样式](skill/progress-bar-studio/assets/style-catalog.svg)

还可以上传喜欢的进度条参考图。AI 会重建它的结构语言，再替换为你的章节、配色和角色，不会把低清截图直接放大成成品。

---

## 详细流程

| 步骤 | Agent 会做什么 | 你确认什么 |
| --- | --- | --- |
| **01 上传素材** | 检查时长、画幅、帧率、音频、输出位置和磁盘空间 | 视频、角色与参考图是否正确 |
| **02 处理角色** | 跳过角色，或生成单张轻动 / 四帧行走素材 | 角色造型、朝向与动作 |
| **03 分析章节** | 转写语音，按内容转折生成时间戳、章节名和划分理由 | 章节名称与边界 |
| **04 样式配色** | 选择预设或拆解参考图，让角色与轨道贴合 | 静态叠加效果 |
| **05 预览导出** | 检查字幕避让、章节切换、透明边缘和导入参数 | 样片与最终交付清单 |

每一步确认后再继续，减少重复生成和模型额度浪费。

---

## 运行要求

- `ffmpeg` 与 `ffprobe`：探测视频、合成预览、导出透明 MOV；
- Python 3：运行素材检查脚本；
- Pillow：拆分四帧素材并生成 WebP 预览；
- 图像生成或编辑能力：根据原角色生成新的行走姿势；
- 足够的磁盘空间：透明 ProRes 4444 文件体积较大。

Skill 已附带以下工具：

| 工具 | 用途 |
| --- | --- |
| `preflight.py` | 检查媒体依赖、ProRes 4444 编码器、输出文件夹与磁盘空间 |
| `estimate_export_size.py` | 根据真实时长、帧率和输出文件夹估算 1080p、2K、4K 文件体积 |
| `prepare_delivery.py` | Step 01 确认后创建版本化交付文件夹，避免同名任务覆盖 |
| `probe_video.sh` | 检查视频尺寸、帧率、时长、音频和磁盘空间 |
| `split_walk_cycle.py` | 拆分四帧精灵图、校验脚底基线、生成 WebP |
| `make_multibg_preview.sh` | 在多种背景上检查透明角色边缘 |
| `verify_alpha_mov.sh` | 逐帧验证 ProRes 4444 Alpha 通道 |

---

## 项目结构

```text
progress-bar-studio/
├── .github/workflows/validate.yml   # GitHub Actions 回归验证
├── CHANGELOG.md                     # 版本与迁移记录
├── LICENSE                          # MIT 开源许可证
├── README.md
├── tests/                           # 小媒体夹具回归测试
└── skill/progress-bar-studio/
    ├── SKILL.md                     # 主工作流与执行规则
    ├── agents/openai.yaml           # Codex 展示信息
    ├── assets/                      # 四种样式与矢量模板
    ├── references/                  # 章节、角色、确认与导出规范
    └── scripts/                     # 视频探测、拆帧和透明度质检
```

## 本地验证

发布前可在仓库根目录执行：

```bash
python3 -m pip install Pillow
python3 -m unittest discover -s tests -v
```

测试会生成临时短视频，覆盖：无音频提示、竖屏探测、损坏媒体、不可写输出目录、磁盘不足、透明 Alpha 校验、同名任务版本化与无角色路径。GitHub Actions 会在推送到 `main` 或提交 Pull Request 时运行同一套检查。

## 许可证

本项目采用 [MIT License](LICENSE)，可使用、修改和分发，但须保留许可证与版权声明。

## 使用提醒

- 上传自己拥有或获准使用的视频、角色和参考图；
- 参考图只用于提取版式结构，不保留第三方角色、Logo、水印或专有图形；
- 正式交付前，在目标剪辑软件中完成一次实际导入测试；
- 渲染透明 MOV 前，确认输出目录有足够空间。
