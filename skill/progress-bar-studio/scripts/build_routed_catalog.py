#!/usr/bin/env python3
"""Build the eight selected no-IP styles; --technical shows all legacy routes."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import style_router as router


def build(technical=False, bold=None):
    font = str(router.classic.choose_font(None, Path.cwd()))
    bold = str(router.classic.choose_font(bold, Path.cwd())) if bold else font
    palette = {"surface": "#FFFFFF", "active": "#C7E97A", "inactive": "#F1FBD0",
               "pill": "#F1FBD0", "text": "#24310F", "quiet": "#435524",
               "outline": "#E0EAC8", "selected": "#C7E97A", "onSelected": "#000000"}
    raw = {"outputWidth": 960, "displayWidth": 480, "fontRegular": font, "fontBold": bold,
           "labelSize": 18, "kickerSize": 11, "character": {"mode": "none"},
           "progressMode": "chapter-weighted", "palette": palette}
    if not technical:raw["visualRevision"]="refined-20261030"
    timeline = {"duration": 10, "fps": 24, "chapters": [
        {"start": 0, "label": "开场", "kicker": "开场"},
        {"start": 3, "label": "安装", "kicker": "第一步"},
        {"start": 7, "label": "验证", "kicker": "第二步"}]}
    entries = list(enumerate(router.catalog(),1)) if technical else [(item["option"],router.REGISTRY[item["styleKey"]]|{"styleKey":item["styleKey"]}) for item in router.creator_catalog()]
    cols=3 if technical else 2
    board = Image.new("RGB", (1620 if technical else 1090, 110+272*((len(entries)+cols-1)//cols)), "#F7F9F0")
    draw = ImageDraw.Draw(board)
    heading = ImageFont.truetype(bold, 30)
    label = ImageFont.truetype(bold, 20)
    small = ImageFont.truetype(font, 17)
    draw.text((26, 20), "技术兼容图册" if technical else "八款精选进度条", font=heading, fill="#24310F")
    draw.text((26, 63), "合成测试 · 显式示例配色 · 无角色 · 各视频仍需按背景、标题与字幕配色", font=small, fill="#56736F")
    for i, (number,spec) in enumerate(entries):
        key = spec["styleKey"]
        if key.startswith("gallery:"):
            envelope = router.migrate_config(raw | {"style": key.split(":")[1]},
                                             router.INSTALLED_ORIGIN, Path.cwd(), Path.cwd(), timeline)
        else:
            config = router.classic.demo_config(key.split(":")[1])
            # The whole board visibly labels synthetic content. Suppress the
            # individual badges only when composing these static comparisons.
            config["demoLabel"] = False
            config["font"],config["fontBold"]=font,bold
            if not technical:config["visualRevision"]="refined-20261030"
            if not technical and key in ('classic:S1','classic:S7'):config['progressMode']='chapter-weighted'
            config["palette"] = {"surface": "#FFFFFF", "active": "#C7E97A", "inactive": "#F1FBD0",
                                 "text": "#24310F", "active-text": "#000000", "outline": "#E0EAC8", "shadow": "#00000000"}
            envelope = {"schemaVersion": 1, "styleKey": key, "rendererConfig": config}
        if not technical:
            selected=router.selected_style(number)
            envelope=router.new_config(str(number).zfill(2),timeline,font,bold,960,
                palette if key.startswith('gallery:') else config['palette'])
            spec={**spec,'name':selected['name']}
        frame = router.build_renderer(envelope, Path.cwd()).frame(4)
        # Crop empty outer margins for a readable static board, never a MOV.
        bounds = frame.getchannel("A").getbbox()
        if bounds:
            frame = frame.crop(bounds)
        frame.thumbnail((480, 185), Image.Resampling.LANCZOS)
        x, y = 20 + (i % cols)*535, 110 + (i // cols)*272
        draw.rounded_rectangle((x, y, x+515, y+252), radius=10, fill="white", outline="#D3DFDC")
        title = key+"  "+spec["name"] if technical else f"{number:02d}  {spec['name']}"
        draw.text((x+16, y+12), title, font=label, fill="#183D39")
        board.paste(frame, (x+(515-frame.width)//2, y+52+(185-frame.height)//2), frame)
    return board


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--technical", action="store_true", help="Show internal route keys for developer review only.")
    parser.add_argument("--font-bold", help="Local bold CJK font file, optional")
    args = parser.parse_args()
    router.classic.save_image(build(args.technical,args.font_bold), args.output)
