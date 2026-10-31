# 完整视觉方案：保存外观，重新理解每条视频

这是 `visual_profile.py` 的独立格式（kind=elleflow-visual-profile），不是旧 schema-4 品牌预设，
不能给旧 preset.json 改名或改版本号冒充。公开 Skill 包不包含任何私人方案或角色。
另见[回访与私有IP库](returning-users.md)：获准四帧单独保存，不受完整外观指纹变化影响。
这样只换样式/升级渲染器时仍复用原IP，不重新生图。

## 保存

在用户明确同意保存、真实样片通过、已获得完整导出授权后，由 Agent 执行：

```text
python scripts/visual_profile.py save --config 当前路由.json --output-dir 私有预设目录/新名称 --sample-approved --final-export-approved
```

用户已要求“保存下来下次快速沿用”时，保存与设为最近默认已有授权，不再重问；加 `--set-default`。
没有此授权时把保存/默认决定合并进综合动态确认，不能用用户沉默代替同意。
默认指针写在该预设目录的父目录，推荐使用已授权私有库/visuals。
用户只需决定保存与否，不需要自己准备 JSON、测坐标或挑字体文件。
已有目录拒绝覆盖；样片豁免不能当成样片批准。CLI 标记是对真实决策的陈述，不代替人类授权。

保存八款可执行路由、外观版本、精确尺寸、配色、字号、进度模式、字体副本、获准的四帧与脚点、
可选放置说明（`--placement 放置说明.json`）、配置和素材校验值，以及渲染实现指纹。
只复制配置实际引用的素材；none 不读取角色图。字体副本仅供私人使用，发布公共包另核查授权。
不保存旧视频、旧章节、旧 sourceId、旧时长/fps，也不创建下一条视频的批准。
外观配置里的字号在 classic 中随宽度计算，gallery 中是明确 displayWidth/labelSize/kickerSize，
均原样保留；配置宽高是条带本身，不代表已合成到原片。

## 快速开始

先检查已知目录，不扫描用户其他文件：

```text
python scripts/visual_profile.py show --default --library-dir 已知私有预设目录
python scripts/visual_profile.py show --profile 私有预设目录/名称/profile.json
```

没有默认方案返回 not_found，是正常首次使用；旧 preset_library.py 仍可兼容检查。
已明确“整套沿用”时不再问同一句。尚未授权才在第一步合并问一次角色、样式、颜色、大小与位置。

当前视频先重新分章并用 validate_chapters.py 检查来源；然后：

```text
python scripts/visual_profile.py restore --profile 原方案/profile.json --timeline 当前章节.json --output 新项目/路由.json
```

`--width 2160` 是显式改变宽度，按比例调整经典条带和角色；不传就保留方案原宽度。
用户明确不要角色时用 `--no-character`，清除角色引用，不读取角色素材，并回收角色空间。
第一步的 `show` 也支持 `--no-character`；用户已指定无 IP 时立即加上，不能先读角色文件再隐藏。
恢复支持当前章节证据里的 label/kicker 或原生渲染标题；不复用旧时轴。
放置说明只作为交付元数据返回，不自动合成到原视频。

每次检查文件、配置和实现指纹。素材缺失、被改动、实现变化时停在受影响的复核，不冒称完全还原。
实现变化并不使角色失效：从独立IP库恢复四帧，保留已知样式偏好，再做待审动态短样。
不因指纹不同清空IP记录或调用生图。没有独立库的旧项目仅按已有明确批准记录迁移角色。
新章节放不下时给实际多行预览或准确简称；不擅自换样式、不复制旧章节来凑版式。
正常样片与本条视频导出授权仍按 confirmation-gates.md，复用不等于授权新的完整导出。

旧 schema-4 没有完整渲染契约，继续按 brand-presets.md / rendering.md 的手动适配核对。
Custom 只有在宿主实现已存在且可移植时才复用；本脚本不把参考截图自动变成新渲染器。
