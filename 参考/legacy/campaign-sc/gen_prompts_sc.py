#!/usr/bin/env python3
"""gen_prompts_sc.py — SC 战役提示生成器：支持 per-arm 题集（修复原 gen_prompts.py 忽略 extra_tasks 的缺陷）。
用法: gen_prompts_sc.py <wave.json> <lib.json> <root>
wave.json: {"name":..., "arms":[...], "tasks_by_arm": {"base":[...], "<arm>":[...]}, "reps":3}
lib.json:  {"techniques":[{"id","prompt",...}]}
"""
import json, os, subprocess, sys

wave_path, lib_path, root = sys.argv[1], sys.argv[2], sys.argv[3]
wave = json.load(open(wave_path, encoding='utf-8'))
lib = json.load(open(lib_path, encoding='utf-8'))
tech = {t['id']: t for t in lib['techniques']}

TASKS_SRC = '/home/pan-ding/bench/tasks'
PREP = '/home/pan-ding/bench/scripts/prepare_task.py'
MARK = '--- TASK INSTRUCTION (verbatim) ---'
reps = int(wave.get('reps', 3))

n = 0
for arm in wave['arms']:
    block = '' if arm == 'base' else '\n' + tech[arm]['prompt'] + '\n'
    for t in wave['tasks_by_arm'][arm]:
        for r in range(1, reps + 1):
            job = f'{arm}/{t}-r{r}'
            scratch = os.path.join(root, 'runs', job, 'work')
            prompt = os.path.join(root, 'runs', job, 'prompt.txt')
            if not os.path.isdir(scratch) or not os.listdir(scratch):
                os.makedirs(scratch, exist_ok=True)
                rc = subprocess.run(['python3', PREP, os.path.join(TASKS_SRC, t), scratch, prompt],
                                    capture_output=True, text=True)
                if rc.returncode != 0:
                    print(f'PREP_FAIL {job}: {rc.stderr.strip()[:120]}')
                    continue
            elif not os.path.exists(prompt):
                subprocess.run(['python3', PREP, os.path.join(TASKS_SRC, t), scratch, prompt],
                               capture_output=True, text=True)
            text = open(prompt, encoding='utf-8').read()
            if block and block.strip()[:40] not in text:
                text = text.replace(MARK, block + '\n' + MARK, 1) if MARK in text else block + '\n' + text
                open(prompt, 'w', encoding='utf-8').write(text)
            n += 1
print(f'gen_prompts_sc done: {n} jobs')
