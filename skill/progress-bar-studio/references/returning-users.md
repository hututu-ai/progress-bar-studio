# 保存一次，下次复用：私有 IP 库与快速通道

## 开场分流

当前明确选择优先：不要角色→none，不读取任何IP；换新角色→处理新图，不套旧IP。
未指定且已有默认整套方案时先检查其角色模式；上次无角色的快速模式保持无角色，不凭另一个旧IP擅自加猫咪。
其余情况检查已知私有库里的默认IP；有效且尚未授权复用时主动问一次：
“上次的小怪四帧已经保存，要沿用 IP 和样式走快速通道吗？也可以只沿用 IP，或本次不加角色。”
若只有IP库、没有可还原的整套方案，准确说“沿用上次IP，样式另选”，不声称整套已还原。
明确“快速模式／整套沿用／用上次IP”的请求已授权相应复用，不再问同一句。
无任何可用记录时才走首次有IP/无IP选择，不假装读取了不存在的记忆。

## 两层保存，不能互相绑死

1. IP库：只含获准四帧、身份说明、步频、脚点、身体基准和相对大小，不含视频、章节或字体。
   与渲染器指纹分离。换样式、换颜色、换视频或渲染器升级，都不默认重新生图。
2. 完整视觉方案：样式、配色、字号、精确尺寸、放置说明、字体和角色引用，继续由 visual_profile.py 管理。
   渲染实现变化只需复核样片；不以样式恢复失败推定原IP已失效。

首次开始时合并说明：“完成并确认后，会把这套IP和样式存入私有方案库，下次可以直接沿用；不想保存告诉我即可。”
本轮/已有明确保存授权时直接执行，不另开一轮保存问卷。当前用户已明确要求“跑过一次后保存”即属授权。
新用户尚无保存意向时在同一综合确认中取得保存决定；不能把沉默当授权。明确不保存就跳过。
只有角色身份/步态/透明已实际批准才入IP库；完整视觉方案需综合短样通过与完整导出授权。
样片豁免不伪造样片批准；如角色已有独立批准，可仅保存IP，不把未看的整体设计存成已验收。

## 私有位置与跨宿主

`python scripts/character_library.py location` 只返回建议位置，不创建文件。
显式已知库优先；否则使用当前用户数据目录的 ProgressBarStudio：macOS Application Support、
Windows LOCALAPPDATA、Linux XDG_DATA_HOME（缺省 ~/.local/share）。先告知位置并检查写入权限。
IP存入characters，视觉方案可存入同根visuals，设默认时只更新小索引，旧版本仍保留。
绝不把用户素材写进公共Skill目录、上传GitHub或依赖当前聊天记忆；不扫描其他用户文件。
宿主不能访问同一私有目录时，提供已保存包让用户导入，不能声称自动跨电脑/云端同步。

## IP保存命令

Agent从已确认素材填写私有spec.json，不让用户编JSON：

```json
{"label":"我的IP","frames":["frame-01.png","frame-02.png","frame-03.png","frame-04.png"],
 "contacts":[[32,70],[32,70],[32,70],[32,70]],"bodyPivotX":32,"cadence":6,"heightRatio":0.08,
 "identityNotes":"按用户原图记录，不能凭空补齐不对称标记"}
```

示例坐标不能照抄；heightRatio为角色可见高度占输出宽度的比例，classic用height/width，
gallery用visibleHeight/displayWidth。已批准旧方案没有bodyPivotX时不擅自添加改变走法。

```text
python scripts/character_library.py save --spec <当前已确认IP.json> --library-dir <私有库> --asset-approved --set-default
python scripts/character_library.py show --default --library-dir <私有库>
python scripts/character_library.py export --default --library-dir <私有库> --engine classic --width 2160 --reuse-authorized --output <新项目/character.json>
```

gallery路线用--engine gallery，默认displayWidth=480；参数由Agent按版式填入。
保存复制原四帧，不重新生成；同素材与几何重复保存会复用现有版本。移动/删除原项目后缓存仍能用。
show只检查已知默认指针和资产，不批准新视频。export也要求实际复用授权，输出拒绝覆盖。
丢失/损坏时说明缺哪份，先恢复备份或换有效记录；只有用户同意重新设计/生成才调用生图。

## 完成后的闭环

综合短样批准、完整导出检查成功后，按已有授权自动保存IP和完整视觉方案，设为最近使用方案。
交付简短说明：“本次IP与样式已保存；下次说‘沿用上次，快速模式’即可。”只有脚本读回成功才能这样说。
保存失败不影响已导出的成品；明确失败原因与方案包位置，不声称下次能自动找到。
真正的快速模式仍重新检查当前成片、语义分章与同步；旧时轴、旧用户批准不转移。
旧视频的“视觉适配通过”也不转移。按 export-and-qc.md 的 Video fit check 核对本次画面；
保留已指定的品牌色与样式，有冲突时只提局部修订，不用换视频作为重新生成IP的理由。
