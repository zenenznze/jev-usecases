# Jev 三项测试：初步录制阶段交接

日期：2026-09-23

状态：阶段性完成，三个测试均保留在“第一次初步录制”阶段；后续恢复时应从本文入口继续，不重新设计或扩大范围。

## 共同边界

- 最终证据以用户亲自进行的连续端到端录制为准。
- 自动化只做最小 preflight，避免录制一开始就失败。
- 浏览器和 Android 回复流程默认停在发送前，等待人工确认。
- 不绕过登录、验证码、权限或平台风控；不自动发布、交易、付款或进行不可逆操作。
- API Key 只从运行时环境注入，不写入仓库、日志或录制证据。
- 三个项目已经进入初步录制阶段，本阶段不再扩展功能。

## 仓库保全状态

主仓库原始上游 `kenhuangus/jev-usecases` 对当前可用账号均为只读，不能直接推送。为确保阶段成果不只保留在本机，完整 `main` 已推送到可写 fork：

- `https://github.com/zenenznze/jev-usecases`
- 阶段交接提交：`22eed3b Document initial recording stage handoff`
- 该 fork 的 `main` 包含项目一、项目二、相关 Jev 验证证据和本交接文档。

若后续需要回馈原上游，应从 fork 发起 PR；不得强推或覆盖原上游。

## 项目一：4S 销售工作台

位置：`experiments/sales-copilot-demo/`

录制入口：

```powershell
$key=[Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY','User')
if ([string]::IsNullOrWhiteSpace($key)) { throw 'TYPESAFE_API_KEY missing' }
$env:TYPESAFE_API_KEY=$key
.venv\Scripts\python.exe experiments\sales-copilot-demo\server.py --port 8787 --mode live
```

录制卡：`experiments/sales-copilot-demo/RECORDING_CARD.txt`

当前成果：

- 中文 4S 销售工作台，支持 Live / Replay。
- 测试 CRM、7 个案例、人工审批与策略门控。
- 正向销售闭环和拒绝/未确认时的反向保护。
- 真实 Jev 调用证据与可独立回读的 CRM 状态。
- Replay、测试和 JSON/语法检查已通过。

本阶段提交：

- `4e9302d`：直接相关 live 脱敏证据。
- `affe1a2`：4S 销售演示工作台。
- `946af8f`：本地录制卡。

后续事项：

- 三个依赖额外生成式模型 Key 的安全工作流尚未完成 live 验证。
- 当前只写入测试 CRM，不代表真实预约系统已成功创建预约。

## 项目二：Feishu 浏览器自动化

位置：`experiments/browser-use-jev-ultrafast/field-demo/`

最短入口：

```powershell
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario A -Query "项目协作"
```

关键文件：

- `README.md`：边界与最短路径。
- `FEISHU_AGENT_PROMPTS.md`：A/B/C 场景提示词和命令。
- `run_feishu_browser.py`：真实 Jev + Browser 控制循环。
- `RECORDING_CARD.md`：录制步骤。

当前成果：

- A：自动导航、搜索、筛选、打开详情和返回。
- B：读取当前可见页面内容并输出结构化数据。
- C：读取真实消息、调用 Jev、填入候选回复并在发送前停止。
- 自动化动作后重新观察页面；不是人工复制消息或纯 CLI gate。
- Python 语法检查与 CLI help 检查通过。

本阶段最终提交：`81155dc Add record-ready Feishu browser automation`

后续事项：

- 首次连接 Chrome 时需要用户点击一次系统级 “Allow remote debugging”。
- 完成允许后，重新运行同一条命令进行第一次连续录制。
- 抖音、小红书、闲鱼尚未纳入本阶段最低可录范围；先以 Feishu 为基线。

## 项目三：Android / ADB 自动化

独立仓库：`C:/Users/joe/projects/jev-use/.tmp/mobile-jev/`

上游原仓库：`droidrun/mobile-jev`

已保全的可写 fork：`https://github.com/zenenznze/mobile-jev`

录制入口：

```sh
pnpm adb-preflight --record
pnpm adb-record --script basic --execute --record --text "capability test"
```

录制卡：`.tmp/mobile-jev/docs/ADB-RECORD-CARD.md`

当前成果：

- ADB 设备连接、Accessibility observe 和可见 Search 定位已验证。
- 真实 Jev 返回模型 `jev-1.13.0`。
- 安全点击、前后截图与连续录屏证据已生成。
- 输入已执行但 UI 回读未确认时会诚实标记 `input_unverified`，不会重复输入。
- 危险动作由安全策略阻止；回复默认停在发送前。
- 测试 55 项通过，lint/typecheck 通过；全仓 format 仍有 44 个既有问题，新增文件格式检查通过。

提交与推送：

- `a311570 Add ADB record-ready Jev demo`
- 原仓库无写权限，提交已推送到 `zenenznze/mobile-jev` 的 `main`。

后续事项：

- 飞书、抖音已安装；小红书、闲鱼仍需用户自行安装并登录。
- 飞书脚本曾因页面跳变被安全机制停止，未伪造成功。
- 若要回馈原项目，应从 fork 创建 PR，而不是强推原仓库。

## Buildsome FDE Demo（本对话新增最高优先级任务）

公网入口：

- `https://buildsome.me/fde-demo/`
- `https://buildsome.me/fde-demo/sales-copilot/`

部署版本：`d0fd295`

当前状态：

- 导航新增“FDE落地demo”。
- 案例页采用客户案例卡片布局。
- 已接入项目一的静态销售副驾驶演示。
- 公网页面明确为 Replay / 演示数据模式，不调用 Jev 或其他外部 API。
- 页面、CSS 和 Replay 脚本均已验证 HTTPS 200；Caddy 正常。

后续事项：

- 服务器仓库 `/home/ubuntu/buildsome/buildsome` 的 GitHub SSH 认证被拒绝。
- 服务器分支在本任务前已有 6 个未推送提交，因此不得盲目推送整个范围。
- 发布产物已有快照：`/home/ubuntu/buildsome/releases/buildsome-d0fd295-20260923-143359.tar.gz`。

## 基础设施与工作流变更

- Herdr 自动修改 tab 名称的机制已移除：
  - `joe-pi`：`44cb41f`
  - `skill-herdr`：`20c0483`
- `skill-wp` 已实现 Durable Supervisor：
  - `52a6033`：持久化控制面。
  - `b6bbccd`：资源所有权文档澄清。
- Durable Supervisor 可用于新 graph 的 `spawn → wait-any → collect → verify → retry → persist → resume`，但不能热接管既有标签页；以后不要把 `/reload` 当作存量任务迁移。

## 恢复顺序

1. 先读本文，不立即重跑 live 操作。
2. 确认目标项目的账号、登录态、设备和 API Key 均由用户显式提供或已在本机配置。
3. 只运行对应项目的最小 preflight。
4. 用户开启摄像头/录屏后，再执行一条录制入口命令。
5. 出现登录、权限、验证码、Chrome remote-debugging 或设备页面跳变时停止，保留真实阻塞，不改成 mock 成功。
