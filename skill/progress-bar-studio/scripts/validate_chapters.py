#!/usr/bin/env python3
"""Check chapter provenance and timing, never claim semantic quality from a pass."""
import argparse
import hashlib
import json
import math
import re
from fractions import Fraction
from pathlib import Path
import subprocess


def frame_rate(value):
    """Accept numeric rates and ffprobe's rational notation, never booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('fps must be a finite positive number or fraction')
    try:
        result = float(Fraction(value))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError('fps must be a finite positive number or fraction') from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError('fps must be a finite positive number or fraction')
    return result


def source_timing(source_video):
    """Use video-track timing, not a possibly longer audio/container duration."""
    metadata = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=duration,avg_frame_rate,r_frame_rate:format=duration',
        '-of', 'json', str(source_video)
    ], text=True))
    streams = metadata.get('streams', [])
    if not streams:
        raise ValueError('source video has no usable video stream')
    stream = streams[0]
    fps = None
    for key in ('avg_frame_rate', 'r_frame_rate'):
        try:
            fps = frame_rate(stream.get(key))
            break
        except ValueError:
            pass
    if fps is None:
        raise ValueError('source video frame rate is unavailable')
    for value in (stream.get('duration'), metadata.get('format', {}).get('duration')):
        try:
            duration = float(value)
        except (ValueError, TypeError):
            continue
        if math.isfinite(duration) and duration > 0:
            return duration, fps
    raise ValueError('source video duration is unavailable')


def validate(plan, transcript, source_video=None, current_policy=False, require_reviewed=False):
    errors, warnings = [], []
    if not isinstance(plan,dict) or not isinstance(transcript,dict):
        return {'ok':False,'errors':['chapter plan and transcript must be JSON objects']}
    def need(ok, message):
        if not ok:
            errors.append(message)
    def number(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)
    duration = plan.get('duration')
    try:
        fps = frame_rate(plan.get('fps'))
    except ValueError as exc:
        return {'ok': False, 'errors': [str(exc)], 'sourceVideoVerified': False}
    if not number(duration) or duration <= 0:
        return {'ok': False, 'errors': ['duration must be a finite positive number'], 'sourceVideoVerified': False}
    timing_fps = fps
    source_id = plan.get('sourceId', '')
    need(isinstance(source_id, str) and bool(re.fullmatch(r'sha256:[0-9a-f]{64}', source_id)),
         'sourceId must contain a SHA-256 hash')
    need(source_id == transcript.get('sourceId'), 'transcript belongs to a different source')
    if source_video:
        digest = hashlib.sha256()
        with Path(source_video).open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        need(source_id == 'sha256:' + digest.hexdigest(), 'source video hash differs')
        source_duration, timing_fps = source_timing(source_video)
        need(math.isclose(fps, timing_fps, rel_tol=0.0001, abs_tol=0.000001), 'source frame rate differs')
        # An incorrect declared rate must never enlarge the source tolerance.
        need(abs(source_duration - duration) <= 1 / timing_fps + 0.001, 'source duration differs')
    tolerance = 1 / timing_fps + 0.001
    segments = transcript.get('segments', [])
    if not isinstance(segments,list) or any(not isinstance(s,dict) for s in segments):
        return {'ok':False,'errors':['transcript segments must be objects in a list']}
    need(bool(segments), 'transcript is empty')
    indexed, ordered = {}, []
    last_start = -1
    for segment in segments:
        sid = segment.get('id')
        need(isinstance(sid, str) and bool(sid) and sid not in indexed, 'segment IDs must be unique strings')
        if not isinstance(sid, str):
            continue
        indexed[sid] = segment
        ordered.append(sid)
        start, end = segment.get('start'), segment.get('end')
        if not number(start) or not number(end):
            errors.append('invalid segment timestamps: ' + sid)
            continue
        need(0 <= start < end <= duration + tolerance and start >= last_start, 'invalid segment order/range: ' + sid)
        need(isinstance(segment.get('text'), str) and bool(segment['text'].strip()), 'missing transcript text: ' + sid)
        last_start = start
    chapters = plan.get('chapters', [])
    if not isinstance(chapters,list) or any(not isinstance(ch,dict) for ch in chapters):
        return {'ok':False,'errors':['chapters must be objects in a list']}
    need(bool(chapters), 'chapters are empty')
    if current_policy:
        from selected_styles import check_new_chapters
        try:check_new_chapters(plan)
        except ValueError as exc:need(False,str(exc))
    used, previous = [], 0
    for i, chapter in enumerate(chapters):
        start, end = chapter.get('start'), chapter.get('end')
        if not number(start) or not number(end):
            errors.append(f'chapter {i + 1}: invalid timestamps')
            continue
        need(abs(start - previous) <= min(0.001, 0.01 / timing_fps) and start < end <= duration + tolerance,
             f'chapter {i + 1}: gap, overlap or invalid range')
        previous = end
        for field in ('label', 'summary', 'boundaryReason', 'openingQuote'):
            need(isinstance(chapter.get(field), str) and bool(chapter[field].strip()), f'chapter {i + 1}: missing {field}')
        ids = chapter.get('segmentIds', [])
        need(isinstance(ids, list) and bool(ids), f'chapter {i + 1}: missing segmentIds')
        if not isinstance(ids, list):
            continue
        used.extend(ids)
        assigned = [indexed[s] for s in ids if isinstance(s, str) and s in indexed]
        need(len(assigned) == len(ids), f'chapter {i + 1}: unknown segment ID')
        if assigned:
            first = assigned[0]
            quote = chapter.get('openingQuote')
            first_text = first.get('text')
            need(isinstance(quote, str) and bool(quote) and isinstance(first_text,str)
                 and quote in first_text, f'chapter {i + 1}: quote not in first assigned segment')
            if i and number(first.get('start')):
                need(abs(start - first['start']) <= tolerance, f'chapter {i + 1}: boundary not aligned with opening segment')
            for s in assigned:
                if number(s.get('start')) and number(s.get('end')):
                    need(s['start'] >= start - tolerance and s['end'] <= end + tolerance,
                         f'chapter {i + 1}: boundary cuts assigned segment {s["id"]}')
        if 'needsReview' not in chapter:
            warnings.append(f'chapter {i + 1}: review state missing; inspect source evidence before setting needsReview=false')
        elif type(chapter['needsReview']) is not bool:
            need(False,f'chapter {i + 1}: needsReview must be boolean')
        elif chapter['needsReview']:
            warnings.append(f'chapter {i + 1}: requires human/agent boundary review')
    if require_reviewed:
        need(not warnings,'unresolved boundary review: resolve it using source evidence before export')
    need(abs(previous - duration) <= min(0.001, 0.01 / timing_fps), 'chapters do not cover video end')
    need(used == ordered, 'segments must be assigned exactly once in original order')
    return {'ok': not errors, 'errors': errors, 'warnings': warnings,
            'sourceVideoVerified': bool(source_video) and not errors,
            'semanticQuality': 'not assessed; review meaning and listen across boundaries'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('chapters')
    parser.add_argument('transcript')
    parser.add_argument('--source-video')
    parser.add_argument('--current-policy',action='store_true',help='New-project 3–5 chapter policy; historical configs are not relabeled')
    parser.add_argument('--require-reviewed',action='store_true',help='Block export preparation while a boundary is still marked needsReview')
    args = parser.parse_args()
    try:
        result = validate(json.loads(Path(args.chapters).read_text(encoding='utf-8')),
                          json.loads(Path(args.transcript).read_text(encoding='utf-8')), args.source_video,args.current_policy,args.require_reviewed)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
