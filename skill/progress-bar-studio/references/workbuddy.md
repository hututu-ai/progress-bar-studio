# WorkBuddy 与其他宿主的最短执行路径

## 导入

通过宿主当前实际提供的本地 Skill 导入入口操作；菜单名称变化时以界面为准，不凭旧说明猜测。
导入包含 progress-bar-studio/SKILL.md、scripts、references、assets 的本地包。
这是本地导入，不是向技能市场发布。开放平台发布有额外元数据要求，不混为一谈。

官方依据（2026-10-29 查阅）：
- https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
- https://open.workbuddy.cn/en/docs/skill

不能因为导入成功就说完整制作已通过。Agent 必须能读取实际 Skill 目录、当前视频，
并在用户授权的输出目录执行脚本。不要寻找另一台电脑的 /Users/... 路径。

## 开始前只做必要检查

1. 从当前消息取得有 IP / 无 IP；缺失才问。无 IP 不要求图像模型。
2. 检查实际可运行的 Python 3.10+：python3、python 或 Windows py -3，选择成功的一个。
3. 在 Skill 根目录运行：
   `python scripts/preflight.py --source-video "当前视频" --output-dir "已授权且存在的目录" --json`。
   python 是上一步确认的解释器，不要求用户照抄占位符。
4. 根据真实工具列表分别记录转写和参考图编辑是否可用。模型名称、能看图、能写提示词
   均不能证明可以编辑角色。未调用验证过的能力记录 unknown。
5. 缺依赖时说明只缺哪一项；询问是否允许安装，不自动改系统、付费或把视频发往第三方。

预检返回实际解释器路径与字体检查。默认 Python 缺 Pillow 时，优先检查宿主已知的其他
现有 Python；选定可用环境后全程保持同一解释器，不反复失败、不用别人机器的绝对路径。
实际章名可用 `--font <当前字体> --text <章名>` 检查；常规体与粗体最终都由渲染器核验字形。

## 两条都能继续的路线

- **无 IP**：当前视频/字幕 → 语义章节与证据 → 无角色渲染配置 → 短样 → 透明 MOV。
- **有 IP**：同样分章；同时检查已授权四帧，或用参考图编辑生成四帧。无生图能力时
  Agent 提供完整外部生成提示词和回传要求。章节和已选样式保留，等待图片时不假装成品完成。

若无 ASR，优先使用当前成片的 SRT/VTT。由 Agent 整理成带 id/start/end/text 的片段，
保留原始字幕；不要要求用户手写全部时间表。没有可靠时间证据时先做设计，不能输出猜测时轴。

## 脚本调用与交付

- 使用数组参数调用命令或正确引用带空格的路径。不同系统不复制 zsh/bash 语法。
- 用 `scripts/style_router.py catalog --creator-facing` 核对当前八款原图号，旧编号不可重解释。
- 用 `scripts/validate_chapters.py <章节证据.json> <转写.json> --source-video <视频>`
  加 `--current-policy` 检查当前来源及3–5章结构；导出前加 `--require-reviewed`。
  生成章节证据的方法见 chapter-analysis.md。
- 无 Bash 时用 `scripts/verify_alpha_portable.py <透明.mov>` 全量解码检查，不把 .sh 失败当成 MOV 失败。
- 六背景审查用 `scripts/make_multibg_preview.py <RGBA.png> <新QC.png> <品牌HEX>`。
  四格准备与拆帧顺序见 character-preparation.md；不依赖 Bash 或全局白色抠图。
- 只有真实 MOV 文件存在且检查通过才说“导出完成”。接力配置、PNG 或网页都不是成品 MOV。
- 样片、完整授权、输出位置、旧预设保存边界遵循主 Skill，不为了“跑通”跳过。

## 首次宿主验收

### 卡住时只恢复受影响一步

| 问题 | 继续方式 |
| --- | --- |
| 私有IP元数据或帧损坏 | 保留旧文件与已选方案，说明缺失/损坏项，优先恢复备份或有效版本；不自动重新生图 |
| 章节缺复核状态 | 回看对应切点再记录布尔值；不把缺状态当通过，不重新询问角色和配色 |
| 四个完整角色跨等分线 | 核对分离且未裁断后重排完整主体；粘连、缺肢、姿态错误不靠拆图修复 |
| 无本地编码能力 | 交付已完成素材和接力配置，注明透明MOV未完成；不把网页或PNG叫成品 |

以上恢复不触发额外付费调用或新的授权；需要超出已有生成额度时先停并说明。

### 从最小实际样片开始

先用公开合成数据做 4 秒、无角色、三章且含两次切章的透明样片；保留实际命令、返回码、
文件和解码报告。然后才测试用户授权的 IP 路线。无角色跑通不代表生图已通过；
本机脚本通过不代表 WorkBuddy 执行过；应用中执行通过也不代表剪映已实际导入。
结果分别记录：读取 Skill / 预检 / 章节证据 / PNG / MOV / Alpha / 图像编辑 / 编辑器导入。

已有证据与尚未测试的项目见 [平台验收边界](platform-validation.md)，不可把旧候选版的
无 IP 合成测试当成新版生图、真实分章或所有 Agent 的完整验收。

可先运行 `python scripts/smoke_test.py --regular <常规体> --bold <粗体> --out <新测试目录>`
检查当前八款PNG和切章时间点。这是标注合成数据的本地测试，不生成角色、不转写或证明MOV/编辑器导入。
