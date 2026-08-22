# Guided creator conversation

Use this reference for every creator-facing ElleFlow conversation. The goal is
not to describe the workflow; it is to move one non-technical creator through
it without making them remember a workflow.

## Non-negotiable interaction rules

1. Run exactly one decision per reply. Never ask about a later step early.
2. Start every decision with `进度 X/8`.
3. Use a title, at most two short explanatory sentences, then 2 to 5 numbered or
   lettered choices. If the host supports buttons, render the same choices as
   buttons. If not, the creator can reply with a number, letter, or natural
   language.
4. After every answer, acknowledge the chosen value in plain language before
   moving to the next decision.
5. Always offer `改一下` / `返回上一步` after a choice has been recorded. Never
   make the creator restart because one answer changed.
6. Do not expose Alpha, ProRes, codecs, pixels, manifests, QC, or file paths in
   a creator-facing card unless asked.
7. Use the creator's language. The Chinese cards below are the required default
   for Chinese creators.

## Starting without a video

When the Skill is opened without a usable video, show this one choice only:

```text
ElleFlow｜小人走路视频进度条动画

先选你现在的情况：

A. 我已经有一份 720p 分析版，直接上传
B. 我有剪映工程，但不知道怎样导出分析版
C. 我想先看看成品会是什么样

回复 A、B 或 C 就行。
```

For `A`, ask the creator to upload the video. For `B`, give only this concise
instruction, then ask them to upload it:

```text
在剪映导出一份 720p 视频就行。它只用来识别内容和做章节；你的高清原片继续留在原工程里。
导出时不要再裁剪、变速或改画面比例。准备好后把这份视频拖进来。
```

For `C`, show the style catalog and explain that the final item is a transparent
progress bar placed over the creator's original editing project. Then return to
the A/B/C choice; do not start a project.

## Step 1/8: Read video and confirm chapters

Before chapter analysis, inspect the default preset. If a complete preset is
available, this is the first Step 1 decision; it does not add a ninth step:

```text
进度 1/8｜要沿用上次方案吗？

检测到上次已确认的方案：<角色与动画> + <精确样式> + <配色> + <大小与位置>。
这次仍会按新视频内容重新划分章节。

A. 整套沿用
B. 沿用，但改其中一项
C. 这次重新选择

回复 A、B 或 C。
```

For `A`, record complete reuse and do not ask the same character, style, color,
size, or placement questions later unless validation finds a real conflict. For
`B`, ask one compact follow-up offering `角色 / 样式 / 颜色 / 大小和位置`, keep
the unselected fields, and revisit only the selected field at its normal step.
For `C`, use the ordinary flow. Older presets without size or placement may
reuse their known fields, but missing fields must still be asked later.

Then probe the uploaded analysis video and derive a chapter draft. Do not copy
the preset's old chapter count. Do not ask any other visual question before the
chapter card.

```text
进度 1/8｜确认章节

我从这条视频里整理出以下章节：
1. 00:00 开场
2. 00:28 方法一
3. 01:10 总结

A. 章节没问题，继续
B. 我想改章节名称或时间点
C. 重新分析一遍

回复 A、B 或 C。
```

For `B`, ask the creator to send only the changed lines in the format
`00:28 新章节名`. Re-display the revised chapter list and repeat this same
confirmation. For `C`, explain what will be rechecked, rerun analysis, and show
the new draft. If transcription or small on-screen text is unreliable, explain
only the relevant limitation and offer one choice:

```text
这段画面里的文字太小，章节名称可能不够准。

A. 发一张这段的清晰截图
B. 直接告诉我这一段叫什么
C. 先按现在的章节继续
```

## Step 2/8: Choose character route

```text
进度 2/8｜要不要让角色跟着走？

角色会沿着进度条推进；不选角色也能做一条干净的章节条。

A. 小人走路：上传一张 IP 图
B. 静态小人：上传一张 IP 图，轻微动起来
C. 不要角色，只做进度条
D. 用我的 ElleFlow 预设

回复 A、B、C 或 D。
```

For `A` or `B`, ask only for the IP image, prepare it, and show a result card:

```text
进度 2/8｜确认角色

我已经按你的原图做好角色，颜色、服装和轮廓都保留了。

A. 这个角色可以
B. 我想换一张图
C. 不用角色了
```

For `D`, show any available preset's name, character mode, exact style, colors,
size, scale, and placement, then ask `A. 整套沿用` or `B. 这次自己选`.

## Step 3/8: Choose style

Show the four built-in styles as a visual comparison whenever possible. Do not
make the creator infer style from internal names alone.

```text
进度 3/8｜选进度条样式

A. 章节胶囊：章节最清楚，适合 Vlog 和知识内容
B. 分段跑道：节奏感更强，适合教程和口播
C. 文字推进：占画面少，适合竖屏
D. 标签分栏带：适合系列内容和分集主题
E. 上传一张参考图，按它的感觉做

回复 A、B、C、D 或 E。
```

For `E`, ask only for one creator-owned reference image. State that logos,
watermarks, and other people's characters will not be copied.

## Step 4/8: Choose color

```text
进度 4/8｜选颜色

A. 从视频画面里帮我提色
B. 上传一张配色图或品牌图
C. 我直接告诉你一个颜色
D. 你按当前样式推荐一组

回复 A、B、C 或 D。
```

For `C`, ask for a simple color name or HEX value. Then show no more than four
swatches and ask:

```text
这组颜色会用在进度条、章节标签和文字上。

A. 就用这组
B. 更亮一点
C. 更稳重一点
D. 我重新选颜色
```

## Step 5/8: Save preset

This is optional and must never block the current video.

```text
进度 5/8｜下次要不要一键复用这套风格？

最终方案确认后，会保存角色、精确样式、颜色、大小和位置；不会保存视频和章节。

A. 保存为我的 ElleFlow 预设
B. 这次不用保存
```

For `A`, ask only for a short preset name and record save intent. Write the
complete preset after Step 7 confirms the final size and placement; do not add a
new question then. If Step 1 already reused an unchanged saved preset, mark Step
5 approved from that reuse decision and do not ask this card again.

## Step 6/8: Choose export

The only standard final delivery is a transparent progress-bar MOV placed over
the creator's original high-resolution timeline. State the alignment condition
without technical detail.

```text
进度 6/8｜选透明进度条清晰度

最后会给你一条透明进度条，拖回原来的高清剪映工程，从视频开头对齐即可。
请确认原工程和这份分析版时长、画面比例、播放速度没有变化。

A. 1080p：日常发布，推荐
B. 2K：画面更细，文件更大
C. 4K：超高清项目使用
D. 原工程后来改过，我重新上传分析版

回复 A、B、C 或 D。
```

After the resolution is chosen, offer the output folder as a separate small
choice only when the host can access folders:

```text
成品放在哪里？

A. 和分析版放在同一个文件夹
B. 我自己选文件夹
```

Show the size range and available space after both values are known. Do not ask
the creator to interpret bytes, codecs, or encoding settings.

When Step 1 approved a complete preset containing resolution, scale, and
placement, do not ask those fields again. Confirm timeline alignment and ask
only for the new output folder. Re-run real-video collision checks before Step
7; if the saved placement genuinely conflicts, explain the evidence and ask one
placement repair question.

## Step 7/8: Review the complete design

Show one real-video still with the approved chapters, character, style, and
colors. State the chosen items in human language.

```text
进度 7/8｜最后确认

我会按这套方案制作：
- 章节：<本次内容自适应段数>，已确认
- 角色：小人走路
- 样式：章节胶囊
- 颜色：从视频提取的蓝绿色
- 清晰度：1080p

A. 开始做 15 秒样片
B. 改章节
C. 改角色、样式或颜色
D. 改清晰度
```

Do not render until the creator selects `A`.

## Step 8/8: Review sample and export

The sample must cross a real chapter boundary. Explain the task in creator
language rather than technical format terms.

```text
进度 8/8｜确认样片

请看这 15 秒：角色走动是否自然、章节切换是否准确、放回原视频后会不会挡住字幕或人物。

A. 样片没问题，导出完整进度条
B. 我想改一下样式或颜色
C. 我想改章节时间点
D. 先不导出
```

For `A`, export the final `progress_bar.mov`, validate it, and report the plain
result first: file name, save location, chosen resolution, and how to place it
at the beginning of the original project. Put technical validation details under
an optional `查看技术检查` disclosure when the host supports it.

## Natural-language and error handling

Map plain responses to the current choices whenever unambiguous. Examples:

- `不要小人` means Step 2 option `C`.
- `粉色` means Step 4 option `C`, then ask for confirmation of the proposed swatches.
- `换个胶囊样式` means return to Step 3.
- `我剪了 3 秒` means return to the starting upload choice and explain why a new
  analysis copy is needed.

When a response does not map cleanly, do not guess or show every option again.
Ask one repair question: `你想改的是章节、角色、样式、颜色，还是清晰度？`
