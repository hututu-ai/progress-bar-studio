#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/video" >&2
  exit 64
fi

input=$1
if [ ! -f "$input" ]; then
  echo "Input not found: $input" >&2
  exit 66
fi

ffprobe -v error -count_frames \
  -show_entries format=duration,size,format_name \
  -show_entries stream=index,codec_type,codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames,sample_rate,channels \
  -of json "$input"

df -h "$(dirname "$input")" | tail -1
