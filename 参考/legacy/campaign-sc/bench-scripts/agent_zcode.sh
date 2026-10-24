#!/bin/bash
# agent_zcode.sh <model> <scratch> <prompt_file>
set -uo pipefail
MODEL="$1"; SCRATCH="$2"; PROMPT="$3"
export PATH="$HOME/.npm-global/bin:$PATH"
exec zcode -p "$(cat "$PROMPT")" --cwd "$SCRATCH" --mode yolo --model "$MODEL"
