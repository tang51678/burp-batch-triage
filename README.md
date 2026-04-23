# burp-batch-triage

<p align="center">
  <img src="https://img.shields.io/badge/OpenClaw-Skill-6f42c1?style=flat-square" alt="OpenClaw Skill">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.x">
  <img src="https://img.shields.io/badge/Workflow-3%20Rounds-0A7EA4?style=flat-square" alt="3 Rounds Workflow">
  <img src="https://img.shields.io/badge/Triage-Low%20Noise-2EA44F?style=flat-square" alt="Low Noise Triage">
  <img src="https://img.shields.io/badge/Artifacts-HTML%20%7C%20JS%20%7C%20JSON-orange?style=flat-square" alt="Artifacts">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="MIT License">
</p>

中文 | [English](#english)

面向 OpenClaw 工作流的低噪声 Web 目标批量研判 Skill。它从用户提供的一个或多个 HTTP/HTTPS URL 出发，围绕真实响应做递进式落地、提取同源页面与资源线索、保留 HTML/JS/CSS 等证据产物，并在最多三轮收敛后输出可复核的 Markdown 结论。

## ✨ 特性 | Features

### 中文

- 以真实 URL 为起点，而不是默认猜测 `/login`、`/swagger`、`/index` 等固定路径
- 三轮最小化验证：入口摸底 → 定向补样 → 结论收敛
- 产物优先：自动落地 HTML、JS、CSS、页面映射、资源索引、轮次 JSON 结果
- 同源递进：从页面真实返回中提取 `script/link/a/form/iframe/meta refresh/window.location` 等线索继续推进
- 结论保守：严格区分 **已确认 / 待验证 / 不能成立**
- 与 Burp 协同：优先通过 Burp bridge 拉取流量，失败时自动回落到直连请求
- 支持批量目标与投递箱自动化模式，适合持续推进而不是一次性扫完
- 只在问题能复核、能站住时生成 `report.md`

### English

- Starts from real user-provided URLs instead of guessing default paths like `/login`, `/swagger`, or `/index`
- Three-round minimal verification flow: entry triage → focused follow-up → closure
- Artifact-first workflow: lands HTML, JS, CSS, page maps, resource indexes, and per-round JSON outputs
- Same-origin progression by following `script/link/a/form/iframe/meta refresh/window.location` hints from real responses
- Conservative conclusion model: **Confirmed / Pending validation / Cannot conclude**
- Burp-aware fetching: prefers Burp bridge first and falls back to direct HTTP requests automatically
- Supports both batch targets and inbox-style automation for continuous low-noise triage
- Generates `report.md` only when a finding is stable and reproducible

## 🎯 适用场景 | Use Cases

### 中文

适用于以下目标形态：

- 登录页、认证门户、统一入口
- 管理后台、运维面板
- SPA 壳站、静态入口页
- 文档服务、办公组件、文件预览系统
- 网关、代理、跳转页
- 前端 JS 中隐藏真实接口链路的系统
- 需要把 URL 快速转成“可复核证据 + 收敛结论”的场景

### English

Suitable for targets such as:

- login portals and authentication entry pages
- admin panels and operator dashboards
- SPA shells and static landing pages
- document services and office-style components
- gateways, proxies, and redirect-heavy entry points
- systems where frontend JS reveals the real API chain
- situations where a URL must be turned into reviewable evidence and grounded conclusions quickly

## 🧠 核心理念 | Core Philosophy

### 中文

这个 Skill 的目标不是泛扫，也不是路径字典起手，而是：

1. 先拿到用户提供 URL 的真实返回
2. 再从真实页面/资源里提取下一步线索
3. 每轮只围绕高价值线索做最小化验证
4. 最终收敛为短、硬、可复核的结论

核心原则：

- 最小化验证优先
- 三轮收敛优先
- 只报能站住的问题

### English

This skill is not designed to be a noisy scanner or a dictionary-first path spray tool. Its intended flow is:

1. fetch the real response of the user-provided URL
2. derive next-step hints from the real page and linked resources
3. keep every round focused on grounded, high-value signals
4. converge into short, hard, reviewable conclusions

Core rules:

- minimal verification first
- converge within three rounds
- only report findings that can stand up to review

## 🏗️ 工作流 | Workflow

### Round 1 — 入口摸底 | Entry Triage

#### 中文

第一轮只围绕原始 URL 和其真实返回展开，不做高噪声扩散扫描：

- 请求用户给定的原始 URL
- 记录状态码、标题、`Content-Type`、跳转位置、响应片段
- 提取 HTML 中的 `script`、`link`、`a`、`form`、`iframe`、`meta refresh`、前端跳转线索
- 下载同源 JS / HTML / CSS / misc 资源
- 从页面和 JS 中提取页面线索、接口线索、参数关键字
- 生成 `page_map.json`、`resource_index.json`、`round1_probe.json`

#### English

Round 1 stays centered on the original URL and what it actually returns. No noisy dictionary expansion is performed.

- request the exact URL provided by the user
- record status code, title, `Content-Type`, redirect target, and body snippet
- extract `script`, `link`, `a`, `form`, `iframe`, `meta refresh`, and frontend redirect hints from HTML
- download same-origin JS / HTML / CSS / misc resources
- extract page hints, API hints, and parameter hints from pages and JS
- produce `page_map.json`, `resource_index.json`, and `round1_probe.json`

### Round 2 — 定向补样 | Focused Minimal Verification

#### 中文

第二轮只围绕第一轮收出的高价值线索继续推进，不平均铺开：

- 第一轮已见到的同源页面入口
- JS/HTML 中收出的请求路径或 action 线索
- 已真实命中的路径或跳转落点
- 与登录、认证、接口访问、页面入口直接相关的低噪声补样

这一轮的目标是尽量拿到真实请求/真实响应样本，而不是理论推断。

#### English

Round 2 only follows the high-value lines grounded in Round 1.

- same-origin page entries already observed
- request paths or action hints extracted from JS/HTML
- paths that were actually hit or revealed by redirects
- low-noise follow-up requests directly tied to auth, entry pages, or access flows

The goal is to obtain real request/response samples rather than speculative theory.

### Round 3 — 结论收敛 | Closure Pass

#### 中文

第三轮只做收敛，不再失控扩展。输出统一收敛到三档：

- **已确认**：有真实响应闭环，可复核
- **待验证**：有迹象，但证据不足以上报
- **不能成立**：当前最小化验证未闭环，应主动降级或排除

如果在第二轮已经拿到稳定问题，可以提前停止，不必强行跑满三轮。

#### English

Round 3 is a closure pass. It does not expand the scope uncontrolled. Every line should end up in one of three states:

- **Confirmed**: backed by reproducible response evidence
- **Pending validation**: promising, but not strong enough to report yet
- **Cannot conclude**: current minimal verification did not close the loop

If a stable issue is already verified earlier, the workflow can stop before forcing all three rounds.

## 📊 输出产物 | Outputs

### 中文

每个目标会按 `<host>_<port>` 归一化后落到：

```text
recon/<host>_<port>/
```

至少会生成：

- `summary.md`
- `round1.md`
- `round2.md`
- `round3.md`
- `artifacts/`

只有问题足够稳定时，才额外生成：

- `report.md`

典型目录结构：

```text
recon/
  example_com_443/
    summary.md
    report.md
    round1.md
    round2.md
    round3.md
    artifacts/
      page_map.json
      resource_index.json
      round1_probe.json
      round2_checks.json
      js/
      html/
      misc/
      <page-bucket>/
        html/
        js/
        misc/
```

### English

Each target is normalized into:

```text
recon/<host>_<port>/
```

At minimum, the workflow produces:

- `summary.md`
- `round1.md`
- `round2.md`
- `round3.md`
- `artifacts/`

Only when a finding is solid and reproducible, it additionally produces:

- `report.md`

Typical directory layout:

```text
recon/
  example_com_443/
    summary.md
    report.md
    round1.md
    round2.md
    round3.md
    artifacts/
      page_map.json
      resource_index.json
      round1_probe.json
      round2_checks.json
      js/
      html/
      misc/
      <page-bucket>/
        html/
        js/
        misc/
```

## 📁 仓库结构 | Repository Structure

```text
burp-batch-triage/
  SKILL.md
  README.md
  references/
    automation.md
    installed-skills.md
  scripts/
    batch_triage.py
    triage_runner.py
    watch_url_file.py
```

## 🔧 脚本说明 | Included Scripts

### `scripts/batch_triage.py`

#### 中文

用于初始化目标目录和 Markdown 骨架。

功能包括：

- 接收命令行 URL 或输入文件
- 去重并保留原始顺序
- 归一化为 `<host>_<port>`
- 创建 `summary.md`、`round1.md`、`round2.md`、`round3.md`
- 可选创建 `report.md`
- 创建目标 `artifacts/` 目录

#### English

Initializes per-target directories and markdown skeleton files.

Capabilities:

- accepts URLs from CLI arguments or an input file
- de-duplicates targets while preserving order
- normalizes them into `<host>_<port>`
- creates `summary.md`, `round1.md`, `round2.md`, `round3.md`
- optionally creates `report.md`
- ensures `artifacts/` exists for each target

示例 | Example:

```bash
python scripts/batch_triage.py https://example.com --output-root recon --with-report-stub
python scripts/batch_triage.py --input-file urls.txt --output-root recon --with-report-stub
```

### `scripts/triage_runner.py`

#### 中文

用于推动已初始化目标按三轮流程继续执行。

功能包括：

- 扫描 `recon/*/summary.md`
- 判断当前待执行轮次
- 执行 Round 1 入口摸底与产物落盘
- 执行 Round 2 定向补样验证
- 执行 Round 3 结论收敛
- 回写 Markdown 总结与 JSON 产物
- 优先走 Burp bridge，失败时回退直连请求

#### English

Advances initialized targets through the three-round workflow.

Capabilities:

- scans `recon/*/summary.md`
- determines which round is pending
- performs Round 1 entry triage and artifact collection
- performs Round 2 focused follow-up checks
- performs Round 3 closure updates
- rewrites markdown summaries and JSON artifacts in place
- prefers Burp bridge fetching and falls back to direct HTTP requests when needed

示例 | Example:

```bash
python scripts/triage_runner.py --recon-root recon --limit 2
```

### `scripts/watch_url_file.py`

#### 中文

用于投递箱式自动化接入新目标。

功能包括：

- 逐行读取 URL 文件
- 去重
- 通过 `.url_watch_state.json` 跳过已初始化目标
- 仅对新增目标调用 `batch_triage.py`
- 为定时任务重复执行维护状态

默认设计中的输入文件：

```text
~/桌面/url.txt
```

#### English

Provides inbox-style automated intake for new targets.

Capabilities:

- reads a URL file line by line
- de-duplicates entries
- skips already initialized targets using `.url_watch_state.json`
- initializes only new targets via `batch_triage.py`
- maintains state for repeated scheduled runs

Default input file in the original design:

```text
~/桌面/url.txt
```

示例 | Example:

```bash
python scripts/watch_url_file.py --input-file ~/桌面/url.txt --workspace <openclaw-workspace> --state-file recon/.url_watch_state.json
```

## 🔗 OpenClaw / Burp 集成 | OpenClaw / Burp Integration

### 中文

这个项目按 OpenClaw 工作区里的 Skill 形态设计，并支持 Burp 代理协同。

`triage_runner.py` 会优先尝试通过 Burp bridge 拉取内容，目标脚本路径为：

```text
~/.openclaw/skills/burp-bridge/scripts/burp_bridge.py
```

默认代理目标为：

```text
http://127.0.0.1:8080
```

如果 Burp bridge 不存在、执行失败，或当前环境不具备该路径，则自动回落到 Python `requests` 直连抓取。

#### 这意味着

- 在 OpenClaw + Burp 环境中，可以把真实抓包链路接进来
- 在普通 Python 环境中，也能作为独立 triage 脚本继续工作

### English

This project is designed as an OpenClaw-style skill and can cooperate with a Burp-based workflow.

`triage_runner.py` first tries to fetch through the Burp bridge located at:

```text
~/.openclaw/skills/burp-bridge/scripts/burp_bridge.py
```

The default Burp proxy target is:

```text
http://127.0.0.1:8080
```

If the bridge is missing or execution fails, the workflow automatically falls back to direct HTTP requests using Python `requests`.

This means the project remains usable in both:

- an OpenClaw + Burp-assisted environment
- a simpler standalone Python environment

## 🤖 自动化模式 | Automation Pattern

### 中文

支持两种运行方式：

#### 1. 对话驱动

直接在会话里给 URL，由当前会话推进处理。

#### 2. 投递箱驱动

把 URL 追加进文件，再通过定时任务持续推进。

推荐自动化链路：

1. 定时运行 `watch_url_file.py`，发现新增目标
2. 定时运行 `triage_runner.py`，推进 pending 目标进入下一轮
3. 每次只推进少量目标，保持串行、低噪声
4. 只有遇到高价值分叉需要人工决策时再中断自动流

### English

Two operating modes are supported.

#### 1. Conversation-driven

Provide one or more URLs directly in the current session and process them there.

#### 2. Inbox-driven automation

Append URLs into a file and let scheduled tasks continue the workflow.

Recommended automation loop:

1. schedule `watch_url_file.py` to discover new targets
2. schedule `triage_runner.py` to advance pending targets
3. keep every run small, serial, and low-noise
4. only interrupt the flow when a high-value branch needs human judgment

## 🧩 与其他 Skill 的配合 | When to Switch to Other Skills

### 中文

默认规则是：

- 先使用 `burp-batch-triage` 做三轮轻量收敛
- 只有当某条线已经明确落入某个漏洞类别时，再切换更专门的 Skill 深挖

典型示例：

- API 深入测试：`conducting-api-security-testing`
- 登录 / token / session / 认证薄弱点：`testing-api-authentication-weaknesses`
- IDOR / 越权：`exploiting-idor-vulnerabilities`
- 数据过曝：`exploiting-excessive-data-exposure-in-api`
- JWT：`testing-jwt-token-security`
- XSS：`testing-for-xss-vulnerabilities`
- SQL 注入：`exploiting-sql-injection-vulnerabilities`

更多可见：

- `references/installed-skills.md`

### English

The default rule is:

- start with `burp-batch-triage`
- only switch to a more specialized skill when a lead clearly lands in a specific vulnerability class

Typical examples:

- deeper API assessment: `conducting-api-security-testing`
- login / token / session weaknesses: `testing-api-authentication-weaknesses`
- IDOR / authorization issues: `exploiting-idor-vulnerabilities`
- excessive data exposure: `exploiting-excessive-data-exposure-in-api`
- JWT: `testing-jwt-token-security`
- XSS verification: `testing-for-xss-vulnerabilities`
- SQL injection follow-up: `exploiting-sql-injection-vulnerabilities`

See also:

- `references/installed-skills.md`

## 🚫 默认避免的行为 | What This Skill Intentionally Avoids

### 中文

默认不做这些事：

- 一上来就跑路径字典或泛扫
- 把纯前端痕迹直接写成漏洞
- 把空响应、占位接口、无差异枚举当成问题
- 在没有证据闭环的情况下扩大高风险动作
- 把“待验证”包装成“已确认”

### English

By default, this workflow avoids:

- dictionary spraying or broad scanning as a first move
- reporting frontend-only traces as confirmed vulnerabilities
- turning empty responses, placeholders, or no-diff enumeration into findings
- expanding into riskier actions without an evidence loop
- promoting “pending validation” into “confirmed” prematurely

## 📦 依赖与要求 | Requirements

### 中文

当前仓库脚本基于 Python 3，依赖：

- `requests`
- `urllib3`

如果希望走 Burp 协同链路，还需要：

- 本地 Burp 代理运行在 `127.0.0.1:8080`
- OpenClaw 的 Burp bridge 脚本位于预期路径

### English

The scripts in this repository currently rely on Python 3 and:

- `requests`
- `urllib3`

For Burp-assisted fetching, you also need:

- a local Burp proxy listening on `127.0.0.1:8080`
- the OpenClaw Burp bridge script in the expected location

## 🚀 快速开始 | Quick Start

### 1. 初始化目标 | Initialize Targets

```bash
python scripts/batch_triage.py https://target1.example https://target2.example --output-root recon --with-report-stub
```

### 2. 推进 triage | Run Triage

```bash
python scripts/triage_runner.py --recon-root recon --limit 2
```

### 3. 文件投递模式 | File-Driven Intake

```bash
python scripts/watch_url_file.py --input-file ~/桌面/url.txt --workspace <openclaw-workspace> --state-file recon/.url_watch_state.json
```

## 📝 GitHub 发布建议 | GitHub Positioning

### 中文

这个仓库最适合被描述为：

- 一个 OpenClaw Skill
- 一个低噪声 Web 目标批量研判工作流
- 一个以证据产物为核心的 triage 工具
- 一个从 URL 驱动到 Markdown 结论收敛的三轮模型

如果放到 GitHub，最重要的是让读者立刻理解：

- 它从真实用户 URL 起步
- 它不是泛扫器
- 它强调证据落地和结果可复核
- 它只在问题站得住时才生成正式报告

### English

This repository is best positioned as:

- an OpenClaw skill
- a low-noise web target triage workflow
- an artifact-first evidence collection helper
- a three-round URL-driven convergence model that ends in markdown conclusions

For GitHub publication, the most important expectations to set are:

- it starts from real user-provided URLs
- it is not a broad noisy scanner
- it emphasizes landed evidence and reviewable outputs
- it only produces formal reports when a finding is strong enough to stand up

---

## English

`burp-batch-triage` is a reusable OpenClaw-oriented skill for low-noise, evidence-driven web target triage. It starts from one or more user-provided HTTP/HTTPS URLs, lands real artifacts, follows same-origin entry hints, extracts page/API/form clues, and advances each target through up to three focused rounds before converging into concise, reviewable markdown conclusions.

If you are reading the English section first, the short version is:

- start from the real URL
- follow only grounded same-origin evidence
- collect artifacts before making claims
- keep conclusions conservative
- generate formal reports only for reproducible findings
