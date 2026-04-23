# 自动化运行说明

## 目标

把 `burp-batch-triage` 从“聊天里收到 URL 后再手动下一步”改成：

1. 定时读取 `~/桌面/url.txt`
2. 自动发现新增 URL
3. 自动初始化 `recon/<host_port>/`
4. 再由定时任务/当前会话继续往下跑 Round 1 ~ Round 3

## 推荐模式

### 模式 A：文件投递 + cron 定时触发

适合你现在的需求：
- 你只往 `~/桌面/url.txt` 里追加 URL
- agent 定时读取
- 有新目标就自动开始
- 不需要你再发下一句“继续”

### 模式 B：文件投递 + cron 唤醒当前 session

如果希望仍在当前会话里持续输出结果，而不是新开独立 run，可用 cron 发送 `agentTurn` 到 current session 绑定任务。

## 当前已补的脚本

- `scripts/watch_url_file.py`
- `scripts/triage_runner.py`

功能：
- `watch_url_file.py`
  - 读取 `~/桌面/url.txt`
  - 去重
  - 跳过已处理目标（按 `host_port` 归一化）
  - 为新增目标调用 `batch_triage.py`
  - 维护状态文件：`recon/.url_watch_state.json`
- `triage_runner.py`
  - 自动扫描 `recon/*/summary.md`
  - 推进 pending 目标进入下一轮
  - 从任意 URL 的真实响应中提取页面/资源/接口线索
  - 产出 `page_map.json` / `resource_index.json` / `round2_checks.json`

## 后续建议

要真正做到“自动继续下一步”，不要只停在初始化目录。还需要再加一层：

1. 定时任务触发 `watch_url_file.py`
2. 定时任务再触发 `triage_runner.py`
3. runner 自动扫描 `recon/*/summary.md`
4. 对 `Status: initialized` 或 `round n pending` 的目标继续跑下一轮
5. 每次只推进一小步并回写 markdown / JSON 产物
6. 人工复核时优先结合 `page_map.json` 与 `resource_index.json` 看真实页面链路

## 关键原则

- 自动化应该是“串行、小步、低噪声”，不是无人值守泛扫
- 默认一次只推进少量目标，避免失控
- 仍然坚持三档结论：已确认 / 待验证 / 不能成立
- 发现需要人工决策的高风险线时，再通知人工介入
