# mcode 官方 harness 对照线 — 设计与排障记录

> 2026-10-21 由"官方harness对照线建设子代理"（GLM 载体）建立。
> 目的：用 mcode 官方 CLI（@minimax-ai/code 0.6.5，anolis）重做 S1 全部 D1-D3 120 题
> （MiniMax-M3.1-Flash 与 MiniMax-M3 两档案），与 af-harness（fix1 mavis 臂）对照，
> 回答"同模型下官方 harness 与自研 harness 差多少"。

## 一、总链路

```
本机(pandev-comp) tools/mcode-dispatch.py（常驻守护）
  │ ssh anolis                                    （解题面）
  │   ├─ /data/bench/mcode-swev/repos/<repo>      12 个上游仓库全量克隆缓存
  │   ├─ /data/bench/mcode-swev/runs/<tid>-<prof> 工作区（git clone --shared + checkout base_commit）
  │   ├─ ~/mcode-swev/auth-sync.py                凭证一致性同步（见 §三）
  │   └─ ~/mcode-swev/run-one.sh                  mcode exec 调用（cal2 复刻）
  │ 收 git diff（git add -A && git diff <base> --binary）
  │ ssh rm -rf 工作区（用后即清）
  └─ 本机 tools/cb-judge.sh 串行判分（sweb.eval 容器 + GNU patch -p1 --fuzz=3
     + 官方 eval_script + swev-judge.py；deepseek-cb 战役验证过的 119 题同链）
```

## 二、调用方式（cal2 遗产复刻）

cal2/mcode-campaign 的 solve.sh / agent_mcode.sh 方式原样复用：

```bash
timeout -k 60 1800 mcode exec --cwd <work> --model <route> --permission full \
  --timeout 25m "$(cat prompt.txt)" > mcode.log 2>&1
```

- 路由名：**m31f = `minimax/MiniMax-M3.1-Flash`**；**m3 = `minimax/MiniMax-M3`**。
  ⚠️ cal2 时代 m31f 叫 `minimax/MiniMax-M3.1-Flash-Preview`；2026-10-20 前后 MiniMax
  managed 路由目录已剔除 Preview 名（报错 `is not available for the "managed_token_plan"
  route (preset cn-prod)`），anolis ~/.minimax/config.yaml 的 models/whitelist 亦同步改名为
  非 Preview（defaultModel 字段仍是旧名，属遗留不一致，不影响 --model 显式指定）。
- prompt = problem_statement + 固定修复指令（只改非测试文件/自验克制/不 commit），
  模板内嵌在 mcode-dispatch.py 的 PROMPT_TMPL；与 deepseek-cb 的 COMMENT_TMPL 同源。
- 补丁收集：`git add -A && git diff <base_commit> --binary`（覆盖新增/修改/删除；
  模型若自行 commit 也被 base 对比罩住）。
- 配额熔断：run-one.sh grep insufficient_balance/402/2067 → rc 42 → 每 profile 独立熔断
  （m31f 免费、m3 走套餐），旗标 /tmp/mcode-dispatch/QUOTA-<prof>。
- turns/tokens：mcode exec stdout 只有最终答复文本，无计量输出 → 记 null（与字段约定一致）。

## 三、排障记录（2026-10-21，exec 报 "Sign in to MiniMax" 的根因链）

cal2 之后 mcode 官方 CLI 在 anolis 上已无法 exec（报 `auth.login_required`）。逐层反汇编
（~/.npm-global/lib/node_modules/@minimax-ai/code/chunks/*.js）定位到三件事：

1. **致命根因：auth-state.json 的 generation 与 auth.json credential 的 generation 不一致。**
   mcode `readUsableCredential()` 硬性要求 `state.generation === credential.generation`，
   不符即抛 credentials 错 → launcher 吞掉 → authContext 为空 → 状态机判 needs-login。
   而 af 主产线的 token 门禁（mcode-token.py，每小时轮换 auth.json，generation 已转到 166）
   从不写 auth-state.json（停在 10-20 登录时的 147）。**两套令牌消费者共用一个 auth.json
   但校验口径不同**——mavis 直调臂只看 accessToken，mcode CLI 还要 generation 对齐。
2. **次要因素**：`auth-state.json.expiresAtMs` 过期（同样只在登录时写一次）；
   `~/.minimax/cli-auth/prod/cn/account-identity.json` 缺失（登录身份档案，含
   tokenFingerprint=sha256(accessToken)，mcode 用它校验身份缓存新鲜度）。
3. **修复 = anolis `~/mcode-swev/auth-sync.py`**，每次 exec 前跑：
   - 令牌余量 <35min → 先 `mcode-token.py refresh`（它自带 flock，与主产线门禁串行；
     35min 覆盖最长 25min 的 exec + 30s minValidity，保证 mcode 全程免刷新、不碰轮换竞态）；
   - flock(auth.json.lock) 内把 auth-state.json 的 generation/expiresAtMs/status 对齐 credential；
   - 重写 account-identity.json 指纹。
   风险注记：mcode 自身若在 <30s 余量时触发刷新，会与门禁走不同锁文件（auth.lock vs
   auth.json.lock）存在理论竞态；auth-sync 的 35min 提前刷新使其在正常运行中永不触发。
   泄漏事故：本次排障中一次 auth.json 结构打印把令牌前 ~30 字符带进子代理转录（事后
   确认字段随即被轮换作废；已记变更日志，后续一律只打印键名/布尔）。

4. 走过的弯路（供后人免重复）：改 auth-state.expiresAtMs 无效；删 lock 文件无效
   （mcode 用的是 auth.lock 文件锁，与 mcode-token.py 的 auth.json.lock 互不冲突）；
   MINIMAX_API_KEY 环境变量注入无效（agent 特性门在 provider 认证之前）；
   account-identity.json 单独补上也不够——generation 对齐才是开关。

## 四、判分与落账

- 判分：`tools/cb-judge.sh /tmp/swev-s1/<tid>.json <patch> <outdir>`，串行
  （cal2 教训：判分须安静防 OOM 假失败；满足 ≤2 红线）。
- 落账（分档命名仿既有 bench-fix1-d<n>-<prof>）：
  - 分档主账：`/tmp/bench-official-mcode-d1-m31f/results.jsonl`（同 d2/d3、-m3）
  - 汇总账：`/tmp/bench-official-mcode-m31f/results.jsonl`、`.../m3/results.jsonl`（全档追加）
  - 每题工件：`runs/<tid>/{patch.diff,mcode.log,apply.log,eval.log,judge.json}`
- 行字段仿 deepseek-cb：profile=mcode-m31f/mcode-m3、scaffold=mcode-official、trial=false、
  turns/model_calls/tokens=null、reward/status/verifier_note 如实。
- 断点续跑：/tmp/mcode-dispatch/state.json 记 (task|profile)→phase，daemon 重启跳过
  judged；QUOTA-<prof> 熔断后续跑只跳过该档案。

## 五、资源纪律

- mcode 并发 2 实例（红线 ≤3，留 1 余量）；判分串行。
- anolis /data/bench/mcode-swev：12 仓库缓存约 2-3G；工作区用后即删；
  /data 余量 <4G 时派发暂停等待（19G 余的 94% 盘上住着 af-factory，谨慎）。
- 解题超时：OS timeout 1800s（cal2 同款），mcode 内层 25m。

## 六、看护与巡检

- 守护：`cd WS && setsid nohup python3 tools/mcode-dispatch.py run >> /tmp/mcode-dispatch.log 2>&1 < /dev/null &`
  （stdin=DEVNULL 教训）；pidfile /tmp/mcode-dispatch/dispatch.pid；心跳文件每题刷新。
- keepalive：factory-keepalive.py 新增 mcode-dispatch 看护对象
  （判据=pidfile 指向活进程 + heartbeat mtime <900s；拉起命令同上）。
- **进度一条命令**：`python3 tools/mcode-dispatch.py summary`
  （分档×分档案 判分/通过/在途/通过率 + QUOTA 旗标）；细节 `tail -30 /tmp/mcode-dispatch.log`。
