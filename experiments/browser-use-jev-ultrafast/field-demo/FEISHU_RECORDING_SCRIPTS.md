# Feishu 网页录制脚本（可直接复制）

> 默认 `LIVE`。真实网页操作由用户完成；本文件不登录、不读取 Cookie、不绕过验证码/风控，不发布、不交易、不发送。

## 0. 启动录制

```bash
cd C:/Users/joe/projects/jev-use
bsk browsers

python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script basic \
  --mode live \
  --browser <browser-id> \
  --run
```

录制面板出现后点击开始；完成脚本后点击 Finish。

- `<browser-id>` 从 `bsk browsers` 复制。
- 录制会启用 `--redact-values`。
- 遇到登录、验证码、风控、页面异常：立即停止并人工接管。
- 发送、发布、交易默认禁止。

## A. 基础操作

启动参数：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script basic --mode live --browser <browser-id> --run
```

录制后依次执行：

1. 打开飞书首页，确认页面可达且不是登录页、验证码页或风控页。
2. 使用页面可见的搜索入口，搜索一个自己有权访问的文档、会话或应用。
3. 等搜索结果稳定，观察结果标题、来源和数量；不要批量滚动。
4. 使用一个页面已有的筛选条件，例如类型、时间或来源。
5. 打开一个搜索结果详情。
6. 停留片刻，记录当前可见的标题、来源、时间；不要复制密码、Token 或私密字段。
7. 点击返回，确认回到搜索结果页。
8. 点击 Finish 停止录制。

观察点：

```text
首页可达 / 登录态正常
搜索词
筛选条件
详情标题和来源
返回后的结果页状态
```

停止条件：完成返回即停止；不编辑、不发布、不交易、不发送。

## B. 可见数据读取

启动参数：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script data --mode live --browser <browser-id> --run
```

录制后依次执行：

1. 打开飞书首页，确认登录态正常。
2. 搜索一个有权访问的文档或会话，并打开详情。
3. 只读取当前屏幕可见内容，不连续翻页、批量滚动或调用隐藏接口。
4. 手工记录以下结构化字段：

```text
source: FEISHU/<页面标题或可见来源>
title: <当前可见标题>
time: <当前可见时间；没有则填 unknown>
status: <当前可见状态；没有则填 unknown>
observed_at: <本地时间>
```

5. 核对来源和标题仍然可见。
6. 点击 Finish 停止录制。

规则：

```text
只记录当前可见且用户有权访问的信息
unknown 保留为 unknown，不猜测补全
不批量抓取、不导出权限外字段
不记录密码、验证码、Cookie、Token
```

## C. 实时回复（发送前停止）

启动参数：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script reply --mode live --browser <browser-id> --run
```

录制后依次执行：

1. 打开飞书消息入口，确认已登录且页面可达。
2. 选择一条真实的新消息。
3. 观察并记录页面标题、会话/来源和消息时间。
4. 将当前可见消息人工复制到下面命令中：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/reply_gate.py \
  --mode live \
  --source "FEISHU/<当前可见页面标题>" \
  --message "<当前可见消息>"
```

5. 读取输出中的 `decision`、`candidate_template`、`human_confirmation_required`。
6. 确认输出包含：

```text
send_allowed: false
human_confirmation_required: true
```

7. 将 `candidate_template` 人工填入飞书回复框。
8. 录下填入前后的页面状态。
9. **停在发送按钮前，绝不点击发送。**
10. 点击 Finish 保存 trace。

如果 Jev 判断不确定、需要补充信息或拒绝联系：保留 `unknown`/拒绝结果，不自行改判，不发送。

## 失败恢复 / 人工接管

```text
登录、验证码、二次验证、风控：用户人工处理
页面变化或元素失效：重新 observe/snapshot，不复用旧 ref
网络失败：保留失败 trace，最多刷新一次，仍失败就停止
误点或发送按钮状态异常：立即停止，不补偿性重复点击
```

## 录制证据

保留 bsk 生成的 trace bundle：

```text
recordings/<本次录制目录>/trace.json
recordings/<本次录制目录>/states/
```

Replay 只能用于复盘，不能冒充 Live 真实站点结果。
