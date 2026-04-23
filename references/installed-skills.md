# installed-skills

当前 `burp` 工作区里，与 Web / API / Burp 实战最相关的已装 skill 速查。

## 默认原则

先使用 `burp-batch-triage` 做三轮最小化验证。
只有当某一条线已经清楚落到某个漏洞类别，再切换更专门的 skill 深挖。

## Burp / 流量

### intercepting-mobile-traffic-with-burpsuite
- 适用：App、H5、移动端接口、代理抓包联动
- 不适用：普通 Web 登录页轻量 triage

### testing-for-xss-vulnerabilities-with-burpsuite
- 适用：已发现明确输入点，需要结合 Burp Repeater/Intruder 做最小化 XSS 验证
- 不适用：还在入口摸底阶段

## API 安全

### conducting-api-security-testing
- 适用：REST / GraphQL / gRPC 接口已经明确，且要系统化验证认证、授权、输入、业务逻辑

### testing-api-security-with-owasp-top-10
- 适用：用户明确要求按 API Top 10 体系走

### testing-api-authentication-weaknesses
- 适用：登录、token、session、验证码、认证链为核心

### detecting-shadow-api-endpoints
- 适用：从前端/流量/代码中挖出文档外接口或隐藏接口

### detecting-api-enumeration-attacks
- 适用：编号、ID、用户名等存在遍历或枚举迹象

### exploiting-excessive-data-exposure-in-api
- 适用：接口响应返回多余字段、敏感字段、前端未展示字段

### exploiting-broken-function-level-authorization
- 适用：普通用户可能调用管理动作、后台功能、管理接口

### detecting-broken-object-property-level-authorization
- 适用：对象字段过量返回、敏感属性可被改写、Mass Assignment 线索

## 常见漏洞

### exploiting-idor-vulnerabilities
- 适用：对象引用可控，且需要最小化越权验证

### testing-jwt-token-security
- 适用：目标明确使用 JWT

### exploiting-jwt-algorithm-confusion-attack
- 适用：JWT 场景下进一步验证算法混淆等问题
- 注意：仅在已进入 JWT 真实验证链时使用

### testing-for-xss-vulnerabilities
- 适用：已看到反射/存储/DOM 输入点

### testing-for-xxe-injection-vulnerabilities
- 适用：存在 XML / SOAP / XML 上传处理

### exploiting-sql-injection-vulnerabilities
- 适用：已有 SQL 注入迹象，如报错、布尔差异、时间差异

### exploiting-sql-injection-with-sqlmap
- 适用：注入迹象已较明确，且需要工具辅助
- 注意：不要对普通未知目标默认直接跑

### exploiting-nosql-injection-vulnerabilities
- 适用：MongoDB / NoSQL 技术栈或参数形态明显

### exploiting-http-request-smuggling
- 适用：前后端代理链复杂，且已有走私线索
- 注意：默认不是轻量 triage 的第一选择

## 通用

### security-auditor
- 适用：代码、配置、认证设计、通用安全基线 review
- 不适用：纯粹的网页登录页轻量三轮摸底

## 实战选择建议

- 登录页 / 管理后台 / 文档服务 / X5 / UReport / OnlyOffice：先用 `burp-batch-triage`
- 明确 API 项目：先 `burp-batch-triage`，再视情况切 `conducting-api-security-testing` 或 `testing-api-authentication-weaknesses`
- 已出现越权迹象：切 `exploiting-idor-vulnerabilities` / `exploiting-broken-function-level-authorization`
- 已出现数据过曝迹象：切 `exploiting-excessive-data-exposure-in-api`
- 已出现 JWT：切 `testing-jwt-token-security`
- 已出现明确 XSS 点：切 `testing-for-xss-vulnerabilities`
- 已出现明确注入迹象：切 SQLi / NoSQLi 对应 skill
