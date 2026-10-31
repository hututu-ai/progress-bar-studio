#!/usr/bin/env python3
"""Full-frame alpha verification with Python + ffmpeg, no shell required."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def verify(path):
    metadata = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ], text=True))
    streams = metadata['streams']
    videos = [s for s in streams if s['codec_type'] == 'video']
    if len(videos) != 1 or any(s['codec_type'] == 'audio' for s in streams):
        raise ValueError('Expected one video stream and no audio')
    video = videos[0]
    if video.get('codec_name') != 'prores' or video.get('profile') != '4444':
        raise ValueError('Expected ProRes 4444')
    # alphaextract fails on an opaque pixel format rather than manufacturing alpha.
    frame_size = video['width'] * video['height']
    frames = transparent = opaque = 0
    with tempfile.TemporaryFile() as error_log:
        process = subprocess.Popen([
            'ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:v:0',
            '-vf', 'alphaextract,format=gray', '-fps_mode', 'passthrough',
            '-f', 'rawvideo', '-pix_fmt', 'gray', 'pipe:1'
        ], stdout=subprocess.PIPE, stderr=error_log)
        try:
            while True:
                frame = bytearray()
                while len(frame) < frame_size:
                    chunk = process.stdout.read(frame_size - len(frame))
                    if not chunk:
                        break
                    frame.extend(chunk)
                if not frame:
                    break
                if len(frame) != frame_size:
                    raise ValueError('Incomplete decoded alpha frame')
                frames += 1
                transparent += 0 in frame
                opaque += 255 in frame
            code = process.wait()
            error_log.seek(0)
            if code:
                raise ValueError(error_log.read(4096).decode(errors='replace'))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
    expected = video.get('nb_frames')
    ok = frames > 0 and transparent == opaque == frames
    if expected and expected != 'N/A':
        ok = ok and frames == int(expected)
    return {'ok': ok, 'decodedFrames': frames, 'framesWithTransparentPixels': transparent,
            'framesWithOpaquePixels': opaque, 'width': video['width'], 'height': video['height'],
            'duration': metadata['format'].get('duration'), 'codec': 'ProRes 4444',
            'editorImport': 'not tested', 'note': 'Visual and source-duration checks remain separate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    args = parser.parse_args()
    try:
        result = verify(Path(args.input).resolve(strict=True))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result = {'ok': False, 'error': str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
