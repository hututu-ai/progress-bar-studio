#!/usr/bin/env python3
"""Opt-in, self-contained visual reuse. Never save a video's timeline or transfer approvals."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import style_router as router
from asset_validation import contained_file, read_object, sha256

KIND='elleflow-visual-profile'

def checksum(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def renderer_fingerprint():
    root=Path(__file__).resolve().parent
    return hashlib.sha256(b''.join((root/p).read_bytes() for p in
        ('render_progress.py','asset_validation.py','font_validation.py',
         'compat_gallery/render_overlay.py','compat_gallery/reference_presets.py'))).hexdigest()

def references(template):
    cfg=template['rendererConfig']
    gallery=template['styleKey'].startswith(('gallery:','legacy:'))
    fields=['fontRegular','fontBold'] if gallery else ['font','fontBold']
    refs=[('font',cfg[field]) for field in fields if cfg.get(field)]
    char=cfg.get('character',{'mode':'none'})
    if char.get('mode','none')!='none':
        refs += [('character',path) for path in char.get('frames',[])]
        if char.get('path'):refs.append(('character',char['path']))
    return refs

def save(config_path, output, sample_approved=False, final_approved=False, placement=None, set_default=False):
    if not sample_approved or not final_approved:
        raise ValueError('保存复用方案需要真实样片批准和完整导出授权；不能把样片豁免标成已批准。')
    original=router.load(config_path)
    renderer=router.build_renderer(original,config_path.parent)
    if renderer.config.demo_label:
        raise ValueError('合成演示不能保存成用户已验收预设。')
    template=copy.deepcopy(original)
    template.pop('timeline',None);template.pop('provenance',None);template.pop('synthetic',None);template.pop('reviewState',None)
    cfg=template['rendererConfig']
    for field in ('duration','fps','chapters','demoLabel'):cfg.pop(field,None)
    # Freeze the actual font choice, even if the old config used auto-detection.
    if original['styleKey'].startswith('classic:'):
        cfg['font']=str(renderer.config.font_path)
        if renderer.config.font_bold_path:cfg['fontBold']=str(renderer.config.font_bold_path)
        cfg['height']=renderer.config.height
    base=(config_path.parent/original.get('assetBase','.')).resolve()
    output=output.resolve()
    if output.exists():raise ValueError('复用方案目录已存在，请用新名称；不覆盖旧方案。')
    output.mkdir(parents=True)
    (output/'assets').mkdir()
    assets={};mapping={}
    for role,value in references(template):
        source=(base/value).resolve()
        if not source.is_file():raise ValueError('复用素材缺失：'+str(source))
        if str(source) not in mapping:
            relative=f'assets/{role}-{len(mapping):02d}{source.suffix.lower()}'
            shutil.copy2(source,output/relative)
            assets[relative]={'role':role,'sha256':sha256(output/relative)}
            mapping[str(source)]=relative
    fields=['fontRegular','fontBold'] if original['styleKey'].startswith(('gallery:','legacy:')) else ['font','fontBold']
    for field in fields:
        if cfg.get(field):cfg[field]=mapping[str((base/cfg[field]).resolve())]
    char=cfg.get('character',{'mode':'none'})
    if char.get('mode','none')!='none':
        if char.get('frames'):char['frames']=[mapping[str((base/v).resolve())] for v in char['frames']]
        if char.get('path'):char['path']=mapping[str((base/char['path']).resolve())]
    template['assetBase']='.'
    profile={'schemaVersion':1,'kind':KIND,'template':template,'assets':assets,'placement':placement,
             'rendererFingerprint':renderer_fingerprint(),
             'historicalApprovals':{'sampleApproved':True,'finalExportAuthorized':True},
             'currentProjectApprovalsInherited':False}
    profile['checksum']=checksum(profile)
    target=output/'profile.json'
    target.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    read(target)
    if set_default:
        pointer=output.parent/'default-visual-profile.json'
        pointer.write_text(json.dumps({'profile':f'{output.name}/profile.json'},ensure_ascii=False)+'\n',encoding='utf-8')
    return {'profile':str(target),'reuseEligible':True,'timelineSaved':False,'currentProjectApprovalsInherited':False}

def read(path, no_character=False):
    profile=read_object(path)
    if profile.get('schemaVersion')!=1 or profile.get('kind')!=KIND:
        raise ValueError('这不是完整视觉复用方案；旧 preset.json 请按旧规则检查，不能改名冒充。')
    signature=profile.get('checksum');payload={k:v for k,v in profile.items() if k!='checksum'}
    if signature!=checksum(payload):raise ValueError('复用配置已变化，请重新检查。')
    if profile.get('historicalApprovals')!={'sampleApproved':True,'finalExportAuthorized':True}:
        raise ValueError('缺少历史样片及导出授权记录。')
    if profile.get('rendererFingerprint')!=renderer_fingerprint():
        raise ValueError('渲染实现已变化，请重新检查短样，不自动视为原样复用。')
    template=profile['template'];router._envelope(template)
    if template.get('assetBase','.')!='.' or 'timeline' in template or any(k in template['rendererConfig'] for k in ('duration','fps','chapters','demoLabel')):
        raise ValueError('视觉方案不得包含旧时间线、批准标记或外部素材根目录。')
    expected={value:role for role,value in references(template)}
    if set(expected)!=set(profile['assets']):raise ValueError('素材清单与渲染配置不一致。')
    for relative,asset in profile['assets'].items():
        if asset.get('role')!=expected[relative]:raise ValueError('素材类型不一致。')
        if no_character and asset['role']=='character':continue
        if sha256(contained_file(path.parent,relative))!=asset['sha256']:
            raise ValueError('复用素材校验失败：'+relative)
    return profile

def restore(path,timeline,output,no_character=False,width=None):
    router.check_new_chapters(timeline)
    profile=read(path,no_character)
    template=copy.deepcopy(profile['template'])
    cfg=template['rendererConfig']
    if no_character:
        if template['styleKey'].startswith('classic:'):
            cfg['height']=max(96,cfg['height']-cfg.get('character',{}).get('height',0))
        cfg['character']={'mode':'none'}
    if width is not None:
        if not 320<=width<=7680:raise ValueError('width must be 320–7680')
        if template['styleKey'].startswith('classic:'):
            scale=width/cfg['width'];cfg['height']=max(96,round(cfg['height']*scale));cfg['width']=width
            if cfg.get('character',{}).get('mode')!='none':cfg['character']['height']*=scale
        else:cfg['outputWidth']=width
    try:template['assetBase']=Path(os.path.relpath(path.parent,output.resolve().parent)).as_posix()
    except ValueError:template['assetBase']=str(path.parent.resolve())  # Windows cross-drive project; the portable profile stays relative.
    result=router.with_timeline(template,timeline)
    renderer=router.build_renderer(result,output.resolve().parent)
    router.classic.ensure_new_output(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'output':str(output.resolve()),'width':renderer.config.width,'height':renderer.config.height,
            'currentProjectApprovalsInherited':False,'placement':profile.get('placement'),
            'sourceVideoVerified':False,'note':'必须先核对本条视频的章节证据；复用不批准本条视频导出。'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    saving=sub.add_parser('save');saving.add_argument('--config',type=Path,required=True);saving.add_argument('--output-dir',type=Path,required=True)
    saving.add_argument('--sample-approved',action='store_true');saving.add_argument('--final-export-approved',action='store_true')
    saving.add_argument('--placement',type=Path);saving.add_argument('--set-default',action='store_true')
    showing=sub.add_parser('show');showing.add_argument('--profile',type=Path);showing.add_argument('--default',action='store_true');showing.add_argument('--library-dir',type=Path);showing.add_argument('--no-character',action='store_true')
    restoring=sub.add_parser('restore');restoring.add_argument('--profile',type=Path,required=True);restoring.add_argument('--timeline',type=Path,required=True);restoring.add_argument('--output',type=Path,required=True)
    restoring.add_argument('--no-character',action='store_true');restoring.add_argument('--width',type=int)
    args=parser.parse_args()
    try:
        if args.command=='save':result=save(args.config.resolve(),args.output_dir,args.sample_approved,args.final_export_approved,read_object(args.placement) if args.placement else None,args.set_default)
        elif args.command=='restore':result=restore(args.profile.resolve(),read_object(args.timeline),args.output,args.no_character,args.width)
        else:
            path=args.profile
            if args.default:
                if not args.library_dir:raise ValueError('--default requires the known --library-dir')
                pointer=args.library_dir/'default-visual-profile.json'
                if not pointer.exists():
                    print(json.dumps({'status':'not_found','reuseEligible':False}));return 0
                path=contained_file(args.library_dir,read_object(pointer)['profile'])
            if not path:raise ValueError('Specify --profile or --default with --library-dir')
            profile=read(path.resolve(),args.no_character)
            cfg=copy.deepcopy(profile['template']['rendererConfig'])
            if args.no_character:cfg['character']={'mode':'none'}
            result={'profile':str(path.resolve()),'reuseEligible':True,'styleKey':profile['template']['styleKey'],
                    'rendererConfig':cfg,'placement':profile.get('placement'),'currentProjectApprovalsInherited':False}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        parser.exit(2,str(exc)+'\n')

if __name__=='__main__':raise SystemExit(main())
