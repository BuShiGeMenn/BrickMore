#!/bin/bash
# 并行下载(6路)+ 慢连接自杀重试 + 双镜像轮换 + 断点续传
set -u
DEST="/e/brick_train/datasets/retile_ab_80000"
mkdir -p "$DEST"
cd "$DEST"

PROXY1="https://gh-proxy.com/https://github.com/BuShiGeMenn/BrickMore/releases/download/lego-retile-ab-80000-20261013-v1"
PROXY2="https://ghfast.top/https://github.com/BuShiGeMenn/BrickMore/releases/download/lego-retile-ab-80000-20261013-v1"

FILES="retile_assembly_metadata.zip"
for i in $(seq -w 1 40); do FILES="$FILES A_retile_assembly_${i}_1000.zip"; done
for i in $(seq -w 1 40); do FILES="$FILES B_retile_assembly_${i}_1000.zip"; done

dl_one() {
  f="$1"
  [ -f "$f.done" ] && return 0
  for attempt in 1 2 3 4 5 6 7 8; do
    URL="$PROXY1/$f"
    [ $((attempt % 2)) -eq 0 ] && URL="$PROXY2/$f"
    # 速度低于 100KB/s 持续 20 秒就断开重试(换连接)
    if curl -sL -C - --retry 2 --connect-timeout 15 --speed-limit 102400 --speed-time 20 -o "$f" "$URL"; then
      echo "[$(date +%H:%M:%S)] OK   $f $(stat -c%s "$f")"
      touch "$f.done"
      return 0
    fi
    sleep 2
  done
  echo "[$(date +%H:%M:%S)] FAIL $f"
  return 1
}
export -f dl_one
export PROXY1 PROXY2

echo $FILES | tr ' ' '\n' | xargs -P 6 -I{} bash -c 'dl_one "$@"' _ {}
# 收尾统计
N=$(ls *.done 2>/dev/null | wc -l)
echo "ALL DONE: $N/81 文件完成"
