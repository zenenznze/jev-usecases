# browser-use/jev-ultrafast 第二测试报告

## 范围

本次只验证 `browser-use/jev-ultrafast`，未执行 mobile-jev，也未等待其他 Agent。

上游地址：<https://github.com/browser-use/jev-ultrafast>
验证时隔离 checkout 的 HEAD：`1231850` (`docs: announce the Cloud waitlist below the README title (#30)`)

## 原始 Demo 可执行性

完成了无需凭据的安装与静态/离线验证：

- `uv sync`：成功，Python 3.13.5，安装 23 个依赖。
- `uv run ruff check .`：通过。
- `uv run pytest`：31 passed。
- `node --check jev_ultrafast/static/app.js`：通过。
- `node --check jev_ultrafast/snapshot.js`：通过。
- `uv build`：成功生成 sdist 和 wheel。
- `uv run jev`：服务正常启动；访问 `http://127.0.0.1:8766/` 返回 HTTP 200，页面标题和 `Start demo` 内容存在。
- Browser Harness 本地能力：Chrome、daemon、active browser connection 均为 OK；Browser Use Cloud auth 为可选项，未配置。

**未宣称完整 live Demo 成功。** 当前环境缺少：

- `TYPESAFE_API_KEY`
- `TEXT_MODEL_API_KEY`

因此没有调用付费模型，也没有伪造 Jev 决策或原始 Google Flights Demo 成功。

## 假 4S CRM E2E

新增可复现实验脚手架：

- `experiments/browser-use-jev-ultrafast/crm.html`
  - 本地假的 4S 销售 CRM；
  - 包含搜索、线索阶段、备注、跟进表单和内存状态读回接口。
- `experiments/browser-use-jev-ultrafast/run_crm_e2e.py`
  - 调用隔离 checkout 中真实的 `Agent`、`Browser`、DOM snapshot、freshness guard 和 Browser Harness Chrome；
  - 默认使用明确标注的离线确定性 stub，不调用模型 API；
  - `--live` 模式只使用真实 Jev/文本模型，凭据缺失时直接阻塞，不降级。

离线命令：

```bash
cd C:/Users/joe/projects/jev-use
uv run --project .tmp/jev-ultrafast python experiments/browser-use-jev-ultrafast/run_crm_e2e.py
```

结果：

- `agent_status=done`
- 13 个浏览器动作，14 个决策循环
- live API calls：0
- 程序独立重新读取并断言：
  - 客户：`张先生`
  - 阶段：`高意向`
  - 备注：`客户询价；周六试驾`
  - 跟进：`试驾 / 周六 / 15:00`

这证明了本地假 CRM 与 Jev Ultrafast 执行层的可复现实验链路，不证明真实 Jev 模型在该业务目标上的选择准确率。

## 主仓库验证

- `python -m py_compile experiments/browser-use-jev-ultrafast/run_crm_e2e.py`：通过。
- `ruff check experiments/browser-use-jev-ultrafast/run_crm_e2e.py`：通过。
- CRM 内联 JavaScript 经 Node syntax check：通过。
- 主仓库 `pytest`（通过隔离验证环境提供依赖）：`96 passed, 38 skipped`；跳过项为 live/API 相关测试。
- `git diff --check`：通过。

## 阻塞与下一条命令

live CRM 的下一步不是猜测成功，而是在全局环境补齐上述两项凭据后执行：

```bash
cd C:/Users/joe/projects/jev-use
uv run --project .tmp/jev-ultrafast python experiments/browser-use-jev-ultrafast/run_crm_e2e.py --live
```

原始 Demo 的 live 启动命令为：

```bash
cd C:/Users/joe/projects/jev-use/.tmp/jev-ultrafast
uv run jev
```

然后打开 `http://127.0.0.1:8766/`。凭据未补齐前，以上 live 路径保持阻塞状态。
