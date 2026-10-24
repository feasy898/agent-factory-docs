# judge_all_v5.sh 判分中转拷贝失效（docker stdin bug）——来自 SC 复测战役的发现

现象：判分结果全部 `infra/no_scratch`。
根因：judge_task 里的中转拷贝 `docker run --rm -v ...: /dst ... bash -c 'while read...' < "$list"` 缺 `-i`，
docker 不转发 stdin，while read 立即 EOF，`$RCAMP/runs` 永远是空的 → remote_judge_v5 找不到 scratch。
实测验证：`echo hello | docker run --rm python:3.11-slim bash -c 'read x; echo $x'` 输出为空；加 `-i` 正常。
修法：该 docker run 加 `-i`。
影响面：confirm-mem-prompt-remote/runs 里的内容疑为旧版脚本残留；若 confirm 波次近期判分出现成片
no_scratch，即此 bug。SC 战役已改用自研 sc_judge.sh（直判，不经中转），不受影响。

---

## 附记（10-17 09:00）：anolis 重启事件

anolis 于 10-17 凌晨宕机/重启（08:58 恢复，uptime 重置）。**所有 watcher 进程已死**。
SC 复测战役已由本会话重新拉起（sc1/sc2 的 glm_watch + sc_watch 共 4 个，断点续跑无数据损失）。
**confirm 战役的 watcher/mcode 也需要主会话重新拉起**——本会话不越权代动，特此告知。
