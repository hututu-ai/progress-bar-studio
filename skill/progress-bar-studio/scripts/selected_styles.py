"""Creator-facing catalog; old renderer IDs never acquire new meanings."""
import copy
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1]/'assets/selected-styles.json').read_text(encoding='utf-8'))

def selected_styles():
    return copy.deepcopy(CATALOG['styles'])

def selected_style(option):
    key = str(option).zfill(2)
    for item in selected_styles():
        if key == item['id']:
            return item
    raise ValueError('请选择当前图册中的 01、02、07、08、10、11、13、15；旧配置请保留原路由。')

def check_new_chapters(timeline):
    chapters=timeline.get('chapters')
    policy=CATALOG['chapterPolicy']
    if not isinstance(chapters,list) or not policy['minimum']<=len(chapters)<=policy['maximum']:
        raise ValueError('新项目默认4章，允许3–5章，最多5章。请按主题合并子步骤、案例和对比，不能平均切或凑数。旧项目用原配置读取。')
    if any(not isinstance(ch,dict) or ch.get('needsReview') for ch in chapters):
        raise ValueError('仍有待复核的章节边界；先结合当前原话和时间证据解决，不自动进入成品配置。')
