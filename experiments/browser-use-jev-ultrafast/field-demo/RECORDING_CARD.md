# 录制卡：Feishu 基线（最短 record-ready 路径）

**Live/Replay 必须显著：** 当前卡默认 `LIVE`。Replay 只能用于复盘，不可冒充真实站点结果。

## 最少前置

1. 用户在 Chromium 中已登录飞书；不提供密码、Cookie、Token。
2. browser-skill 扩展已连接；验证码、登录、风控全部由用户人工处理。
3. 页面允许用户读取当前可见内容；不批量抓取，不绕过权限。

检查：

```bash
cd C:/Users/joe/projects/jev-use
python experiments/browser-use-jev-ultrafast/field-demo/record_ready.py preflight --site feishu
bsk browsers
```

若 preflight 显示无连接，先打开扩展并连接浏览器，再重跑；不要重试页面操作。

## 一步启动录制

从 `bsk browsers` 取得 `<browser-id>` 后：

```bash
cd C:/Users/joe/projects/jev-use
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script basic --mode live --browser <browser-id> --run
```

这条命令会直接启动 `bsk record start ... --redact-values`。录制面板出现后点击开始，照 `record_scripts/01_feishu_basic.md` 执行，结束时点击 Finish。trace bundle 是权威原始步骤证据。

控制台可选入口：

```text
experiments/browser-use-jev-ultrafast/field-demo/record_console.html
```

控制台只记录动作名、时间和 LIVE 标识，不保存消息正文；“发送”按钮永远锁定。

## 三个可直接照录的脚本

- A：`record_scripts/01_feishu_basic.md`
- B：`record_scripts/02_feishu_visible_data.md`
- C：`record_scripts/03_feishu_reply_before_send.md`

每个脚本都可以把上面的 `--script basic` 替换成 `data` 或 `reply`。

### A：基础操作（首条建议录制）

1. 进入飞书首页，确认页面可达和已登录。
2. 搜索一个用户有权访问的文档、会话或应用。
3. 观察搜索结果，做一个可见筛选。
4. 打开一个详情页，记录标题/来源/时间等可见事实。
5. 返回结果页。
6. 停止录制；不编辑、不发布、不交易、不发送。

**观察点：** 页面标题、搜索词、筛选条件、详情标题、返回后的结果状态。

### B：可见数据读取

1. 在 A 的详情页停留。
2. 只记录当前屏幕可见且用户有权访问的字段：`source/title/time/status`。
3. 在控制台或本地笔记中结构化记录，并保留来源 URL/页面标题。
4. 不滚动加载大量内容，不导出私密字段，不绕过权限/验证码/反爬。

**证据：** bsk trace + 页面截图/observe；敏感输入启用 `--redact-values`。

### C：实时回复（发送前停止）

1. 打开真实新消息，先录下消息所在页面和时间。
2. 人工复制当前可见消息，运行：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/reply_gate.py \
  --mode live \
  --source "FEISHU/<visible-page-title>" \
  --message "<人工复制的可见消息>"
```

3. 读取 Jev 的意图、风险、下一动作和人工确认标志。
4. 将 `candidate_template` 填入回复框，录下填入前后页面状态。
5. **停在发送按钮前。** 不点击发送；若页面变化或出现风控，点击人工接管/停止录制。

## 失败恢复与人工接管

- 登录、验证码、二次验证、风控：停止自动化，用户人工完成；完成后重新 observe/snapshot。
- 页面变化/元素引用失效：不要复用旧 ref；重新 observe，再决定是否继续。
- 网络失败：保留失败 trace，刷新一次；仍失败则停止并人工接管。
- 误点风险：立即停止；不要补偿性重复点击。
- 发送、发布、交易：默认禁止；只有用户另行明确授权的独立任务才可讨论。

## 交付边界

达到“用户能复制一条命令、看到 LIVE 标识、开始录制 A”的状态即停止本轮。抖音、小红书、闲鱼仅使用 `sites.json` 的入口和各自登录/风控前置，不等待四站兼容。
