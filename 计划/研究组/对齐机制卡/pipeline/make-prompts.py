#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make-prompts.py — 生成 15 个对齐目标的机制卡提示词（m3.1f headless 批产用）。
输出: prompts/<slug>.txt
"""
import os

TMPL = """你是 agent 框架机制分析员。仅凭你训练知识内的资料，为对齐目标「{target}」产出一份"机制卡"，作为 Agent 定义 DSL 翻译的输入草稿（只是草稿，最终通过与与否由我们的编译器裁定，所以要做忠实的机制提炼与映射预判）。

{fallback}

硬性输出纪律：
1. 禁止调用任何工具/命令，禁止读写文件——你的最终回复文本就是交付物。
2. 最终回复必须且只能是一份 Markdown 机制卡（中文），无前言、无结语、无道歉。
3. 卡的第一行写 `<!-- TARGET: {target} -->`；若你实际改写了别的框架，第二行加 `<!-- ACTUAL: 实际写的框架名 -->`；若你对该目标知识明显不足，另加一行 `<!-- CONFIDENCE: LOW -->`，并且只写有把握的内容，绝不编造（宁短勿错）。
4. 固定六节，节标题逐字使用以下字面：
## ① 核心机制
## ② 组件清单
## ③ 数据与上下文流
## ④ 失败处理与停止条件
## ⑤ 预算与评估方式
## ⑥ DSL 表达点清单

各节内容要求：
① 一段话说清：该框架/论文解决什么问题、核心循环/执行模型是什么。
② 组件清单：角色/循环/记忆/工具/通信/状态等，用表格（组件|类型|职责），不漏关键组件。
③ 数据与上下文流：谁在什么时机看到什么上下文——消息如何构造、记忆/工件何时注入或交接、状态存在哪、何时对谁可见。
④ 失败处理与停止条件：重试/回退/自省修复/早停/终止判据，逐条列。
⑤ 预算与评估方式：token/轮次/成本如何控制；论文或框架用什么基准与消融评估效果。
⑥ 分两类列清单：
   (a) 可映射为"标准拓扑+组件"的机制——映射预判要写到这个粒度，如「ReAct=单节点循环」「MetaGPT=流水线+结构化工件交接」；
   (b) 预计需要 DSL 逃逸舱的机制（运行时不可静态声明、DSL 表达不了的部分）——逐条给出并说明理由（例：运行时动态生成/改写图结构=逃逸舱）。

全文 800~2000 字，宁可精炼不可空洞；不确定的内容明确标注"存疑"。
"""

TARGETS = [
    ("react", "ReAct（Reasoning + Acting 交错循环，Yao et al. 2022）", ""),
    ("reflexion", "Reflexion（语言化自我反思 + 情景记忆 Buffer，Shinn et al. 2023）", ""),
    ("voyager", "Voyager（Minecraft 开放世界：自动课程 + 可执行代码技能库 + 迭代提示机制，Wang et al. 2023）", ""),
    ("swe-agent", "SWE-agent（Agent-Computer Interface，仓库级软件工程修复，Princeton 2024）", ""),
    ("memgpt", "MemGPT（LLM 操作系统式分层记忆：主上下文/外部上下文 + 自编辑记忆函数调用，Packer et al. 2023）",
     "备选说明：若你对 MemGPT 的机制细节了解有限，可改写 Mem0（记忆层产品化框架），但须按输出纪律第 3 条如实标注 ACTUAL。"),
    ("metagpt", "MetaGPT（软件公司 SOP 多角色流水线：PM/架构师/工程师/QA + 结构化工件交接，Hong et al. 2023）", ""),
    ("camel", "CAMEL（Role-Playing 双代理协作 + Inception Prompting，Li et al. 2023）",
     "备选说明：若你对 CAMEL 的机制细节了解有限，可改写 AgentVerse（动态多智能体编队），但须按输出纪律第 3 条如实标注 ACTUAL。"),
    ("gptswarm", "GPTSwarm（把 agent 建模成可优化的计算图/蜂群：节点=操作，边=信息流，可自动优化图结构，Zhuge et al. 2024）", ""),
    ("delm", "Agensh（去中心化多智能体协作框架）",
     "备选说明：若你不知道 Agensh，可改写 DeLM（去中心化协作）；若两者都不了解，选你最了解的一个『去中心化/无中心协调者的多智能体协作』框架或论文（例如基于共识/合约/区块链协调的 MAS），但须按输出纪律第 3 条如实标注 ACTUAL——张冠李戴比留白更糟。"),
    ("mad", "Multi-Agent Debate（多智能体辩论：多解生成 + 多轮互相批判 + 裁决收敛，如 Du et al. 2023 / Kahneman-Tversky 式辩论）", ""),
    ("aflow", "AFlow（工作流自动搜索：把 agent 工作流表达成 MCTS 搜索空间中的代码图，自动生成+评分工作流，Zhang et al. 2024）", ""),
    ("adas", "ADAS（Automated Design of Agentic Systems：用 meta agent 编程式设计/合成新 agent 系统设计，Hu et al. 2024）", ""),
    ("langgraph", "LangGraph StateGraph（LangGraph 的状态图编排：节点=函数，共享 State，条件边/循环/检查点/interrupt）", ""),
    ("autogen", "AutoGen（v0.4+ autogen-agentchat）的声明式 Team 配置（可序列化为 JSON）：RoundRobinGroupChat / SelectorGroupChat / MagenticOne 等团队拓扑、termination conditions、participant agent 声明", ""),
    ("crewai", "CrewAI 的 YAML 装配方式（agents.yaml + tasks.yaml 声明角色/目标/背景故事/任务期望与分配，Process=sequential/hierarchical）", ""),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "prompts")
    os.makedirs(outdir, exist_ok=True)
    for slug, target, fallback in TARGETS:
        fb = fallback if fallback else "（无备选目标。）"
        text = TMPL.format(target=target, fallback=fb)
        with open(os.path.join(outdir, slug + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote", slug, len(text))


if __name__ == "__main__":
    main()
