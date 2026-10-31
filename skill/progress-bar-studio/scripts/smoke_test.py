#!/usr/bin/env python3
"""Offline selected-eight smoke test; no ASR, image generation, approvals or publishing."""
import argparse
import json
from pathlib import Path
import style_router as router
from selected_styles import selected_styles
from asset_validation import image_bytes, publish_new_files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--regular',required=True);p.add_argument('--bold',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.out.exists() and any(a.out.iterdir()):raise ValueError('Use a new or empty smoke-test directory')
        palette={'surface':'#FFFFFF','active':'#C7E97A','inactive':'#F1FBD0','text':'#000000',
                 'active-text':'#000000','outline':'#B8CC8B','shadow':'#00000000',
                 'pill':'#F1FBD0','quiet':'#52603B','selected':'#C7E97A','onSelected':'#000000'}
        timeline={'duration':4,'fps':30,'chapters':[{'start':0,'end':1,'title':'问题','label':'问题'},
            {'start':1,'end':2.5,'title':'方法','label':'方法'},{'start':2.5,'end':4,'title':'验证','label':'验证'}]}
        files={};results=[]
        for spec in selected_styles():
            tokens=router.DEFAULT if spec['styleKey'].startswith('gallery:') else router.classic.TOKENS
            colors={k:palette[k] for k in tokens}
            cfg=router.new_config(spec['id'],timeline,a.regular,a.bold,1080,colors)
            cfg['synthetic']=True
            renderer=router.build_renderer(cfg,Path.cwd())
            for index,t in enumerate((0,29/30,1,74/30,2.5,4)):
                im=renderer.frame(t)
                if im.getchannel('A').getextrema()!=(0,255):raise ValueError('Missing transparent/opaque pixels')
                files[f"{spec['id']}-{index}.png"]=image_bytes(im)
            files[f"{spec['id']}.json"]=(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode()
            results.append({'id':spec['id'],'frames':6,'width':renderer.config.width,'height':renderer.config.height})
        report={'technicalChecks':'passed','styles':results,'semanticASR':'not-tested',
                'imageGeneration':'not-tested','editorImport':'not-tested','userApproved':False}
        files['report.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
        publish_new_files(a.out,files)
        print(json.dumps(report,ensure_ascii=False));return 0
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
