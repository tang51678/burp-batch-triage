---
name: burp-batch-triage
description: Batch-process one or more web target URLs with a Burp-style minimal-verification workflow. Use when the user provides one or more HTTP/HTTPS URLs and wants a reusable, low-noise reconnaissance+triage skill that can land HTML/JS/CSS artifacts, follow same-origin entry pages, extract page/api/form hints, and advance targets through up to 3 focused rounds with per-target markdown outputs such as summary.md and report.md. Suitable for login pages, admin panels, APIs, portals, static entry pages, document services, and similar web attack surfaces where the goal is to quickly turn a URL into reproducible grounded findings instead of stopping at the first page.
---

# Burp Batch Triage

按“最小化验证、三轮收敛、只报能站住的问题”的方式，逐个处理用户给出的 URL。

这个 skill 的目标不是只适配某一个站，而是把 **任意给定 HTTP/HTTPS URL** 先落地、再递进、再收敛：
- 先抓首个 URL 的真实响应
- 再从页面里抽取 `script/link/a/form/iframe/meta refresh/window.location` 等线索
- 继续跟进同源入口页面
- 把 HTML / JS / CSS / 关键补样结果落到 `artifacts/`
- 最后把结论收敛到 markdown，而不是停在“首页没 JS”或“只看了 /login”

支持两种运行方式：
- 对话驱动：用户在聊天里直接给 URL，再由当前会话推进
- 投递箱驱动：定时读取 `~/桌面/url.txt`，自动发现新增 URL，并继续推进后续轮次，尽量减少人工逐句干预

## Core workflow

默认目标是 **围绕用户给定原始 URL 的真实返回逐步收敛**，而不是用模板路径或通用字典先行探测。

### 1. Normalize input targets

支持三种输入：
- 聊天里直接给多行 URL
- 提供一个 `.txt` / `.md` 文件，文件中按行列出 URL
- 固定投递文件 `~/桌面/url.txt`，供定时任务自动读取

执行前先做这些动作：
- 去重
- 去掉空行
- 保留原始 URL 顺序
- 为每个目标生成稳定目录名：`<host>_<port>` 或 `<host>_<default-port>`

默认输出目录：
- `recon/<normalized-target>/`

默认状态文件：
- `recon/.url_watch_state.json`

每个目标至少生成：
- `summary.md`

如果走自动化模式，还应维护：
- 目标是否已初始化
- 当前进行到第几轮
- 是否已完成

如果存在可稳妥上报的问题，再额外生成：
- `report.md`

可选落盘：
- `round1.md`
- `round2.md`
- `round3.md`
- `artifacts/`
  - `round1_probe.json`
  - `round2_checks.json`
  - `page_map.json`
  - `resource_index.json`

### 2. Round 1: entry triage

首轮只做轻量摸底，不做扩散式扫描。

这一轮的唯一入口是：
- 用户给定的原始 URL
- 以及该 URL 真实返回后导出的同源页面/资源

优先确认：
- 这是登录页、SPA、真实后端、文档服务、网关，还是静态壳
- 首个 URL 本身有没有外链 JS/CSS/iframe/form/action/跳转线索
- 如果首个页面本身资源不多，是否存在可继续递进的同源入口页
- 是否暴露静态前端资源，可帮助定位真实登录链、真实请求封装、后续动作页
- 是否存在明显的未登录接口候选

常见动作包括：
- 请求用户给定 URL，而不是假定必须是首页或 `/login`
- 拉取页面里的 JS/CSS/HTML 资源并从中提取真实登录链、接口名、参数名、页面入口
- 继续跟进页面中的同源 `a href` / `form action` / `iframe src` / `meta refresh` / 前端跳转线索
- 为后续人工复核生成 `page_map.json` 与 `resource_index.json`
- 记录标题、版本、关键路径、状态码、`Location`、`Content-Type`

不要在这一轮做高噪声字典扫描。
不要把 `/login`、`/swagger-ui.html`、`/v2/api-docs`、`/index.html` 之类固定路径当成默认起手式。

### 3. Round 2: focused minimal verification

只围绕 Round 1 收出的重点线继续打，不要平均铺开。

Round 2 默认优先级应是：
- 真实页面已出现的同源页面入口
- JS 中能落地到真实请求形态的 action / path / request hint
- Round 1 已命中的真实入口或跳转落点

不要把第三方文档链接、库作者链接、规范说明链接、静态图片/CSS 文件当成 Round 2 默认补样目标。

这一轮不应只盯 JS 接口线索，也要覆盖：
- 页面入口线索
- `form action` 目标
- `iframe src` / 页面跳转线索
- Round 1 已命中的低风险重点路径

优先验证：
- 验证码爆破
- 验证码回显
- 注册码回显
- 无效验证码
- 验证码复用
- 短信轰炸
- 批量注册
- 验证码可绕过
- 验证码长度/复杂度缺陷
- 返回包修改
- 关系校验
- 未授权登陆/访问
- 用户名覆盖
- 无效用户名
- 登录框持久
- 请求参数篡改
- 空密码或空用户名绕过
- 源码泄露
- 敏感信息泄露
- 错误信息泄露
- 万能密码
- 用户名爆破
- 账号锁定
- 密码重置漏洞
- 用户名枚举
- RCE漏洞/nday
- 弱口令
- XSS
- CSRF
- SQL注入
- 垂直越权
- 水平越权
- 未授权API访问
- UID拼接
- URL跳转
- Host头注入
- 路径遍历

此轮应尽量拿到真实请求/真实响应样本，不用理论推断代替验证结果。

### 4. Round 3: closure pass

第三轮只允许继续深挖 1~2 条最有价值的线。

目标是把结论收敛为：
- 已确认
- 待验证
- 不能成立

如果在第二轮已经拿到稳定、可复核、可上报的问题，可提前停止该目标，直接进入报告整理，不必强行跑满三轮。

## Reporting rules

### summary.md

每个目标都生成 `summary.md`，至少包含：
- 目标 URL
- 处理时间
- 三轮做了什么
- 已确认
- 待验证
- 不能成立
- 下一步建议

### report.md

只有在问题“能站住、能复核、能实锤”时才生成 `report.md`。

`report.md` 应包含：
- 问题标题
- 风险级别（保守）
- 影响路径
- 复现步骤
- 关键请求/响应样本
- 为什么能成立
- 当前验证边界（明确说明未扩展到哪些高风险动作）

不要把以下内容直接写成漏洞：
- 仅前端痕迹
- 仅异常现象但未闭环
- 空响应占位接口
- 没有差异的猜测性枚举
- 需要重度利用才能判断的线索

## Conclusion discipline

始终用以下三级表达：
- **已确认**：有真实响应闭环，可复核
- **待验证**：有迹象，但当前样本不足以上报
- **不能成立**：本轮最小化验证未形成闭环，应主动排除或降级

禁止把“待验证”包装成“已确认”。

## Directory layout

推荐目录结构：

```text
recon/
  example.com_443/
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

说明：
- 根层 `artifacts/js|html|misc` 用于保存入口页直接导出的资源
- `artifacts/<page-bucket>/...` 用于保存递进页面各自的资源包
- 同时保留 `page_map.json` 与 `resource_index.json`，便于人工复核定位，不建议随意平铺所有文件到目标根目录

如果目标无洞，也保留 `summary.md`，不要什么都不落。

## Automation pattern

当用户明确要求“自动跑”“定时读取 URL 文件”“不想每一步都人工继续”时，按下面方式改造：

1. 使用 `scripts/watch_url_file.py` 读取 `~/桌面/url.txt`
2. 只把新增目标初始化到 `recon/<host_port>/`
3. 再配合 cron，让 agent 定时继续推进 pending 目标
4. 每次推进一小步，不做失控泛扫
5. 只有遇到明显高风险、需要人工决策的分叉时才中断自动流

自动化模式下，默认不要要求用户每轮都再发一句“继续”。

参考文件：
- `references/automation.md`

Bundled automation scripts：
- `scripts/watch_url_file.py`
- `scripts/triage_runner.py`
  - 支持从任意输入 URL 起步，递进发现同源页面并落地 HTML / JS / CSS / 线索产物
  - 生成 `page_map.json` / `resource_index.json`，便于后续人工复核
  - Round 2 默认只围绕同源页面入口、请求线索、真实命中路径做低噪声补样，不拿第三方文档链接和静态资源名直接发请求

## Tooling guidance

### Default tools

优先使用：
- `exec`：运行最小化探测脚本、curl、python requests 脚本
- `read` / `write`：整理结果与报告
- `edit`：增量修正文档

### When to use other installed skills

当前 `burp` 工作区里已装的安全相关 skill，按场景选用：

- `conducting-api-security-testing`
  - 当目标已明确是 REST / GraphQL / gRPC API，且需要按 API 安全思路系统化验证时使用

- `testing-api-security-with-owasp-top-10`
  - 当用户明确要按 API Top 10 体系过一遍时使用

- `testing-api-authentication-weaknesses`
  - 当重点是登录、token、session、认证机制薄弱点时使用

- `exploiting-broken-function-level-authorization`
  - 当已发现普通用户可能访问管理功能、管理接口或高权限动作时使用

- `detecting-broken-object-property-level-authorization`
  - 当接口可能返回过多字段、可改写敏感属性或存在对象属性级越权时使用

- `exploiting-excessive-data-exposure-in-api`
  - 当响应明显返回了前端未展示但接口传输了敏感字段时使用

- `detecting-api-enumeration-attacks`
  - 当对象 ID / 用户名 / 编号遍历线索已经出现，且需要判断是否存在枚举/BOLA/IDOR 风险时使用

- `exploiting-idor-vulnerabilities`
  - 当已拿到可疑对象引用接口，只差做最小化越权验证时使用

- `testing-jwt-token-security`
  - 当认证材料中已出现 JWT，且需要验证签名、算法、授权相关问题时使用

- `exploiting-jwt-algorithm-confusion-attack`
  - 仅在已确认目标使用 JWT 且具备授权测试前提时使用

- `testing-for-xss-vulnerabilities` / `testing-for-xss-vulnerabilities-with-burpsuite`
  - 当已看到明确反射点、存储点或前端渲染输入点时使用，不要默认全站打 XSS

- `testing-for-xxe-injection-vulnerabilities`
  - 仅在目标明确处理 XML / SOAP / 上传 XML 时使用

- `exploiting-sql-injection-vulnerabilities` / `exploiting-sql-injection-with-sqlmap`
  - 仅在已有注入迹象、报错、延时、拼接线索时使用；默认不要对普通目标直接上 sqlmap

- `exploiting-nosql-injection-vulnerabilities`
  - 仅在接口、参数、技术栈显示 NoSQL 痕迹时使用

- `intercepting-mobile-traffic-with-burpsuite`
  - 当目标来自 App、小程序、移动端接口联动时使用

- `security-auditor`
  - 当任务更偏通用安全审计或代码/配置层 review，而非纯 Web 流量验证时使用

### Selection rule

默认先用本 skill 的三轮轻量工作流。只有当某条线已经明确落到某个漏洞类别时，再切换调用更专门的 skill 深挖。

不要一开始就把所有已装 skill 全部用一遍。

## Output style

默认中文。

结论表达要短、硬、可复核，保留：
- 精确 URL
- 参数名
- 状态码
- 关键报错
- Cookie / Header / 关键字段
- 版本、路径、标识符

## Bundled resources

- `scripts/batch_triage.py`：批量目标处理与目录落盘入口
- `references/installed-skills.md`：当前 burp 工作区已装 skill 的场景速查
