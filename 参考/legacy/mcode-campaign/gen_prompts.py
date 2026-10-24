#!/usr/bin/env python3
"""gen_prompts.py — anolis 侧：为波次生成每 (arm, task, rep) 的 scratch 与 prompt.txt。
prompt = PREAMBLE + [技术块(非base臂)] + 任务指令。技术块插在 PREAMBLE 之后、任务指令之前。
用法: gen_prompts.py <wave.json> <lib.json> <camp_root>
"""
import json, os, subprocess, sys

wave_path, lib_path, root = sys.argv[1], sys.argv[2], sys.argv[3]
wave = json.load(open(wave_path, encoding='utf-8'))
lib = json.load(open(lib_path, encoding='utf-8'))
tech = {t['id']: t for t in lib['techniques']}
tool_tech = {t['id']: t for t in json.load(open(lib_path.replace('prompt-library-prompt', 'prompt-library-tool'), encoding='utf-8'))['techniques']} if os.path.exists(lib_path.replace('prompt-library-prompt', 'prompt-library-tool')) else {}
tech.update(tool_tech)

TASKS_SRC = '/home/pan-ding/bench/tasks'
PREP = '/home/pan-ding/bench/scripts/prepare_task.py'
MARK = '--- TASK INSTRUCTION (verbatim) ---'

arms = ['base'] + wave['techniques']
arm_tasks = {a: wave['core_tasks'] for a in arms}  # 统一题集
reps = int(wave.get('reps', 2))

n = 0
for arm in arms:
    tech_block = ''
    if arm != 'base' and arm in tech:
        tech_block = '\n' + tech[arm]['prompt'] + '\n'
    for t in arm_tasks[arm]:
        for r in range(1, reps + 1):
            job = f'{arm}/{t}-r{r}'
            scratch = os.path.join(root, 'runs', job, 'work')
            prompt = os.path.join(root, 'runs', job, 'prompt.txt')
            if not os.path.isdir(scratch) or not os.listdir(scratch):
                os.makedirs(scratch, exist_ok=True)
                # prepare_task.py <task_dir> <scratch> <prompt_out>
                rc = subprocess.run(['python3', PREP, os.path.join(TASKS_SRC, t), scratch, prompt],
                                    capture_output=True, text=True)
                if rc.returncode != 0:
                    print(f'PREP_FAIL {job}: {rc.stderr.strip()[:120]}')
                    continue
            else:
                if not os.path.exists(prompt):
                    subprocess.run(['python3', PREP, os.path.join(TASKS_SRC, t), scratch, prompt],
                                   capture_output=True, text=True)
            # 注入技术块（若尚未注入）
            text = open(prompt, encoding='utf-8').read()
            if tech_block and tech_block.strip()[:40] not in text:
                if MARK in text:
                    text = text.replace(MARK, tech_block + '\n' + MARK, 1)
                else:
                    text = tech_block + '\n' + text
                open(prompt, 'w', encoding='utf-8').write(text)
            n += 1
print(f'gen_prompts done: {n} jobs')
