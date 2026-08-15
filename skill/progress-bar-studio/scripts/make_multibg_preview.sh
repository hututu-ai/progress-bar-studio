#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 /path/to/rgba.png /path/to/review.png" >&2
  exit 64
fi

input=$1
output=$2
if [ ! -f "$input" ]; then
  echo "Input not found: $input" >&2
  exit 66
fi

width=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=width -of default=nw=1:nk=1 "$input")
height=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=height -of default=nw=1:nk=1 "$input")

ffmpeg -nostdin -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=white:s=${width}x${height}" \
  -f lavfi -i "color=c=black:s=${width}x${height}" \
  -f lavfi -i "color=c=red:s=${width}x${height}" \
  -f lavfi -i "color=c=blue:s=${width}x${height}" \
  -f lavfi -i "color=c=#FBEAF0:s=${width}x${height}" \
  -f lavfi -i "nullsrc=s=${width}x${height},geq=r=if(mod(floor(X/16)+floor(Y/16)\\,2)\\,215\\,250):g=if(mod(floor(X/16)+floor(Y/16)\\,2)\\,215\\,250):b=if(mod(floor(X/16)+floor(Y/16)\\,2)\\,215\\,250)" \
  -i "$input" \
  -filter_complex "[0:v][6:v]overlay=0:0[a];[1:v][6:v]overlay=0:0[b];[2:v][6:v]overlay=0:0[c];[3:v][6:v]overlay=0:0[d];[4:v][6:v]overlay=0:0[e];[5:v][6:v]overlay=0:0[f];[a][b][c][d][e][f]xstack=inputs=6:layout=0_0|${width}_0|0_${height}|${width}_${height}|0_$((height * 2))|${width}_$((height * 2))[out]" \
  -map "[out]" -frames:v 1 "$output"
