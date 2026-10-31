#!/usr/bin/env python3
"""Private, renderer-independent four-frame reuse. Never generates images or saves a timeline."""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import tempfile
import sys
from asset_validation import (contained_file, read_object, read_image, validate_frames,
                              default_contact, visible_contact, publish_new_files, sha256)

KIND='elleflow-character'


def default_library():
    # A predictable private user-data root, never inside an installed/public Skill.
    if sys.platform=='win32':
        root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))
    elif sys.platform=='darwin':root=Path.home()/'Library/Application Support'
    else:root=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    return root/'ProgressBarStudio'


def checksum(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()


def check_geometry(spec, images):
    if not isinstance(spec,dict):raise ValueError('Cached geometry is invalid; restore the saved IP metadata before reuse')
    contacts=spec.get('contacts')
    if contacts is None:contacts=[list(default_contact(im)) for im in images]
    if not isinstance(contacts,list) or len(contacts)!=4:raise ValueError('Need four foot contacts')
    contacts=[list(visible_contact(im,p)) for im,p in zip(images,contacts)]
    cadence=spec.get('cadence',6);ratio=spec.get('heightRatio',.08)
    for name,value,low,high in (('cadence',cadence,1,12),('heightRatio',ratio,.001,.3)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'Invalid {name}')
    result={'contacts':contacts,'cadence':cadence,'heightRatio':ratio}
    pivot=spec.get('bodyPivotX')
    if pivot is not None:
        if isinstance(pivot,bool) or not isinstance(pivot,(int,float)) or not math.isfinite(pivot) or not 0<=pivot<images[0].width:
            raise ValueError('bodyPivotX outside source canvas')
        result['bodyPivotX']=pivot
    return result


def set_default(library, manifest):
    relative=manifest.resolve().relative_to(library.resolve()).as_posix()
    # Only the last-used pointer changes; immutable character versions remain intact.
    handle,name=tempfile.mkstemp(prefix='.character-pointer-',suffix='.json',dir=library)
    try:
        with os.fdopen(handle,'w',encoding='utf-8') as f:json.dump({'character':relative},f,ensure_ascii=False)
        os.replace(name,library/'default-character.json')
    finally:
        if Path(name).exists():Path(name).unlink()


def save(spec, base, library, asset_approved=False, make_default=False):
    if not asset_approved:raise ValueError('Save only an actually approved identity/gait/transparent asset, not an unreviewed draft')
    if not isinstance(spec,dict) or set(spec)-{'label','frames','contacts','bodyPivotX','cadence','heightRatio','identityNotes'}:
        raise ValueError('Character spec cannot contain video, timeline, style or approval-transfer fields')
    label=spec.get('label')
    if not isinstance(label,str) or not label.strip() or len(label)>100:raise ValueError('Need a short character label')
    paths=spec.get('frames')
    if not isinstance(paths,list) or len(paths)!=4 or any(not isinstance(p,str) or not p for p in paths):raise ValueError('Need four local frame paths')
    paths=[(Path(base)/p).expanduser().resolve() for p in paths]
    images=[read_image(p,transparent=True,image_format='PNG') for p in paths]
    validate_frames(images);geometry=check_geometry(spec,images)
    notes=spec.get('identityNotes','')
    if not isinstance(notes,str) or len(notes)>4000:raise ValueError('identityNotes must be short text')
    payload={'schemaVersion':1,'kind':KIND,'label':label.strip(),'identityNotes':notes,
        'geometry':geometry,'frameSize':list(images[0].size),'frames':[],
        'historicalAssetApproval':True,'currentProjectApprovalsInherited':False}
    files={}
    for i,p in enumerate(paths):
        name=f'frames/frame-{i+1:02}.png'
        payload['frames'].append({'path':name,'sha256':sha256(p)})
        files[name]=p.read_bytes()
    payload['checksum']=checksum(payload)
    # Content identity makes saving the same approved IP idempotent, not another generation.
    directory=Path(library)/'characters'/('ip-'+payload['checksum'][:20])
    manifest=directory/'character.json'
    if directory.exists():
        current=read(manifest)
        if current['checksum']!=payload['checksum']:raise ValueError('Existing character differs; preserve it and choose another library')
        reused=True
    else:
        # Build the complete bundle before the private pointer is made visible.
        directory.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.new-character-',dir=directory.parent) as staging:
            stage=Path(staging);(stage/'frames').mkdir()
            publish_new_files(stage/'frames',{Path(n).name:data for n,data in files.items()})
            publish_new_files(stage,{'character.json':(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()})
            read(stage/'character.json')
            # Reserve the version directory. Never replace even an empty existing directory.
            directory.mkdir()
            try:
                import shutil
                for p in stage.iterdir():
                    if p.is_dir():shutil.copytree(p,directory/p.name)
                    else:shutil.copy2(p,directory/p.name)
                read(manifest)
            except BaseException:
                # Keep incomplete evidence unindexed; never advertise a partial bundle as reusable.
                raise
        reused=False
    if make_default:set_default(Path(library),manifest)
    return {'character':str(manifest.resolve()),'label':payload['label'],'reuseEligible':True,
            'alreadySaved':reused,'imageGenerationCalls':0,'currentProjectApprovalsInherited':False}


def read(path):
    path=Path(path);data=read_object(path)
    if data.get('schemaVersion')!=1 or data.get('kind')!=KIND or data.get('historicalAssetApproval') is not True:
        raise ValueError('Not an approved private four-frame character')
    if data.get('checksum')!=checksum({k:v for k,v in data.items() if k!='checksum'}):raise ValueError('Character metadata changed')
    if data.get('currentProjectApprovalsInherited') is not False:raise ValueError('Character reuse must not approve a new project')
    rows=data.get('frames')
    if not isinstance(rows,list) or len(rows)!=4:raise ValueError('Need four cached frames')
    for row in rows:
        if (not isinstance(row,dict) or not isinstance(row.get('path'),str)
                or not isinstance(row.get('sha256'),str)
                or re.fullmatch(r'[0-9a-f]{64}',row['sha256']) is None):
            raise ValueError('Cached frame entry is invalid; restore the saved IP metadata, do not regenerate without consent')
    if not isinstance(data.get('geometry'),dict):
        raise ValueError('Cached geometry is invalid; restore the saved IP metadata before reuse')
    paths=[contained_file(path.parent,row['path']) for row in rows]
    if len(set(paths))!=4:raise ValueError('Need four distinct cached paths')
    if any(sha256(p)!=row['sha256'] for p,row in zip(paths,rows)):raise ValueError('Cached frame missing or modified; restore it, do not regenerate without consent')
    images=[read_image(p,transparent=True,image_format='PNG') for p in paths]
    validate_frames(images)
    if data.get('frameSize')!=list(images[0].size):raise ValueError('Cached frame size changed')
    check_geometry(data['geometry'],images)
    return data


def locate_default(library):
    pointer=Path(library)/'default-character.json'
    return contained_file(Path(library),read_object(pointer)['character']) if pointer.exists() else None


def export_character(path, engine, width, display_width=480, reuse_authorized=False):
    if not reuse_authorized:raise ValueError('Ask whether to reuse the previous IP, unless this request already authorizes it')
    data=read(Path(path));geometry=data['geometry']
    if not 320<=width<=7680 or not 240<=display_width<=1920:raise ValueError('Invalid output/display width')
    frames=[str(contained_file(Path(path).parent,row['path'])) for row in data['frames']]
    if engine=='classic':
        char={'mode':'walk-cycle','approved':True,'frames':frames,'contacts':geometry['contacts'],
              'height':geometry['heightRatio']*width,'cadence':geometry['cadence']}
    elif engine=='gallery':
        char={'mode':'four-frame','frames':frames,'anchors':[{'x':x,'y':y} for x,y in geometry['contacts']],
              'visibleHeight':geometry['heightRatio']*display_width,'cycleFps':geometry['cadence']}
    else:raise ValueError('Engine must be classic or gallery')
    if 'bodyPivotX' in geometry:char['bodyPivotX']=geometry['bodyPivotX']
    return char


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('location')
    s=sub.add_parser('save');s.add_argument('--spec',type=Path,required=True);s.add_argument('--library-dir',type=Path)
    s.add_argument('--asset-approved',action='store_true');s.add_argument('--set-default',action='store_true')
    for name in ('show','export'):
        c=sub.add_parser(name);c.add_argument('--character',type=Path);c.add_argument('--default',action='store_true');c.add_argument('--library-dir',type=Path)
        if name=='export':
            c.add_argument('--engine',choices=('classic','gallery'),required=True);c.add_argument('--width',type=int,required=True)
            c.add_argument('--display-width',type=int,default=480);c.add_argument('--reuse-authorized',action='store_true');c.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        library=(getattr(a,'library_dir',None) or default_library()).expanduser().resolve()
        if a.command=='location':result={'library':str(library),'created':False}
        elif a.command=='save':result=save(read_object(a.spec),a.spec.resolve().parent,library,a.asset_approved,a.set_default)
        else:
            if bool(a.character)==bool(a.default):raise ValueError('Choose --character or --default')
            path=a.character.resolve() if a.character else locate_default(library)
            if path is None:
                if a.command=='export':raise ValueError('No saved IP; do not claim reuse or trigger generation automatically')
                result={'status':'not_found','reuseEligible':False,'imageGenerationCalls':0}
            elif a.command=='show':
                data=read(path);result={'status':'ready','character':str(path),'label':data['label'],
                    'reuseEligible':True,'imageGenerationCalls':0,'currentProjectApprovalsInherited':False}
            else:
                char=export_character(path,a.engine,a.width,a.display_width,a.reuse_authorized)
                publish_new_files(a.output.parent,{a.output.name:(json.dumps(char,ensure_ascii=False,indent=2)+'\n').encode()})
                result={'output':str(a.output.resolve()),'imageGenerationCalls':0,'currentProjectApprovalsInherited':False}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
