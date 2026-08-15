#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/prores4444.mov" >&2
  exit 64
fi

input=$1
if [ ! -f "$input" ]; then
  echo "Input not found: $input" >&2
  exit 66
fi

codec=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name -of default=nw=1:nk=1 "$input")
profile=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=profile -of default=nw=1:nk=1 "$input")

if [ "$codec" != "prores" ] || [ "$profile" != "4444" ]; then
  echo "Expected ProRes 4444; got codec=$codec profile=$profile" >&2
  exit 2
fi

ffprobe -v error -count_frames \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_name,profile,codec_tag_string,width,height,r_frame_rate,pix_fmt,nb_read_frames \
  -of json "$input"

stats_file=$(mktemp -t progress-alpha-stats.XXXXXX)
trap 'rm -f "$stats_file"' EXIT HUP INT TERM

ffmpeg -nostdin -hide_banner -loglevel error -i "$input" \
  -vf "format=rgba,alphaextract,signalstats,metadata=print:file=$stats_file" \
  -f null -

frames=$(grep -c '^frame:' "$stats_file" || true)
transparent=$(grep -c '^lavfi.signalstats.YMIN=0$' "$stats_file" || true)
opaque=$(grep -c '^lavfi.signalstats.YMAX=255$' "$stats_file" || true)

echo "alpha_frames=$frames"
echo "frames_with_zero_alpha=$transparent"
echo "frames_with_full_alpha=$opaque"

if [ "$frames" -eq 0 ] || [ "$transparent" -ne "$frames" ] || [ "$opaque" -ne "$frames" ]; then
  echo "Alpha verification failed" >&2
  exit 2
fi

echo "Alpha verification passed"
