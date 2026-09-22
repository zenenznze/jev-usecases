# 4S 销售副驾驶 · 最短录制入口

这是**模拟销售场景、真实 Jev 调用、测试 CRM 执行**。没有真实预约系统，不声称预约成功。

## 一条启动命令

在仓库根目录执行：

```bash
.venv\\Scripts\\python.exe experiments/sales-copilot-demo/server.py --port 8787
```

打开：<http://127.0.0.1:8787/>

默认是 `REPLAY`，不需要 Key；切换到 `LIVE · 真实 Jev` 后，服务进程必须有 `TYPESAFE_API_KEY`。Windows PowerShell 启动 Live：

```powershell
$key = [Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY','User')
if ([string]::IsNullOrWhiteSpace($key)) { throw 'TYPESAFE_API_KEY missing at User scope' }
$env:TYPESAFE_API_KEY = $key
.venv\\Scripts\\python.exe experiments/sales-copilot-demo/server.py --port 8787 --mode live
```

Key 只进入当前子进程，不显示、不写入文件。

## 录制卡（按顺序）

1. 页面确认顶部出现 `REPLAY · 可重复`；切换到 Live 后应出现 `LIVE · 真实 Jev`。
2. 点击 **一键重置**，选择案例 **高意向：i3 / 预算 / 置换 / 月供 / 周六到店但未确认**。
3. 点击 **重新判断本轮**。录制画面应看到客户事实、模型推断、未知信息分栏，以及模型版本、请求 ID、延迟、输入指纹。
4. 观察策略卡：客户表达周六到店意向，但未确认；系统显示 `await_customer_confirmation`，CRM 预约仍为“未写入”。
5. 点击 **人工确认客户已明确同意到店 → 写入测试 CRM**。
6. 观察 **CRM 独立读回**：阶段变为高意向，出现“人工确认”测试记录；明确说明这不是实际预约。
7. 选择 **取消并明确勿联系**，点击 **一键重置** 后重新判断；预期显示 `block_outreach`，审批按钮不可推进。
8. 选择 **模糊/反讽**，一键重置后点击重新判断；预期进入人工复核，不沿用上一轮结果。

## 录制失败时

点击 **一键重置**，重新执行第 2 步；Live 网络失败会显示错误，不会自动降级为 Replay，也不会写 CRM。

## 最小预检

```bash
.venv\\Scripts\\python.exe experiments/sales-copilot-demo/run_replay.py
.venv\\Scripts\\python.exe -m pytest experiments/sales-copilot-demo/test_demo.py -q
```

Replay 证据写入 `evidence/replay-evidence.json`。Live 证据可用以下命令生成；它只写模型返回和测试 CRM 读回，不写 Key：

```powershell
$key = [Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY','User')
$env:TYPESAFE_API_KEY = $key
.venv\\Scripts\\python.exe experiments/sales-copilot-demo/run_live.py
```
