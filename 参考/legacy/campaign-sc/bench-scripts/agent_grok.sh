#!/bin/bash
# agent_grok.sh <model> <scratch> <prompt_file>  (cal2: grok via hk SOCKS5 proxy)
set -uo pipefail
MODEL="$1"; SCRATCH="$2"; PROMPT="$3"
export PATH="$HOME/.grok/bin:$PATH"
px="socks5h://100.64.0.3:1080"
export HTTPS_PROXY="$px" HTTP_PROXY="$px" ALL_PROXY="$px"
export NO_PROXY="localhost,127.0.0.1,::1,100.64.0.0/10,.ts.net,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
OUT=$(mktemp)
cd "$SCRATCH"
script -qec "grok --cwd \"$SCRATCH\" --always-approve --max-turns 150 --model \"$MODEL\" --output-format json --prompt-file \"$PROMPT\"" "$OUT" </dev/null >/dev/null 2>&1
rc=$?
tail -c 4000 "$OUT" | tr -d "\r" | sed "s/\x1b\[[0-9;]*[A-Za-z]//g" | tail -c 2500
if grep -qiE "insufficient credits|quota exceeded|usage cap|rate limit exceeded|HTTP 402|error code: 429|计划用量已达上限" "$OUT"; then
  touch /home/pan-ding/bench/QUOTA
  rm -f "$OUT"; exit 42
fi
rm -f "$OUT"
exit $rc
