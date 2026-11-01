#!/bin/bash
# 下载 lego-retile-ab-80000-20261013-v1 全部 83 个文件(断点续传+重试)
set -u
DEST="/e/brick_train/datasets/retile_ab_80000"
mkdir -p "$DEST"
BASE="https://gh-proxy.com/https://github.com/BuShiGeMenn/BrickMore/releases/download/lego-retile-ab-80000-20261013-v1"

cd "$DEST"
FILES="SHA256SUMS.txt download_manifest.json retile_assembly_metadata.zip"
for i in $(seq -w 1 40); do
  FILES="$FILES A_retile_assembly_${i}_1000.zip"
done
for i in $(seq -w 1 40); do
  FILES="$FILES B_retile_assembly_${i}_1000.zip"
done

TOTAL=$(echo $FILES | wc -w)
N=0
FAIL=0
for f in $FILES; do
  N=$((N+1))
  for attempt in 1 2 3; do
    if curl -sL -C - --retry 3 --connect-timeout 20 -o "$f" "$BASE/$f"; then
      SZ=$(stat -c%s "$f" 2>/dev/null || echo 0)
      echo "[$(date +%H:%M:%S)] $N/$TOTAL $f ${SZ} bytes OK"
      break
    elif [ $attempt -eq 3 ]; then
      echo "[$(date +%H:%M:%S)] $N/$TOTAL $f FAILED"
      FAIL=$((FAIL+1))
    else
      sleep 5
    fi
  done
done
echo "ALL DONE failed=$FAIL"
