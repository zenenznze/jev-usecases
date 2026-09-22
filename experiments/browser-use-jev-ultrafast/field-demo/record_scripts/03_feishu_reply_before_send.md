# Feishu C：实时回复录制脚本（LIVE，发送前停止）

**目标：** 读取真实新消息 → Jev 判断意图/风险/下一动作 → 生成候选回复或模板 → 填入输入框；绝不点击发送。

## 启动

```bash
bsk browsers
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script reply --mode live --browser <browser-id> --run
```

## 逐步动作

1. 打开飞书消息入口，确认已登录且页面可达。
2. 选择一条真实的新消息；确认该消息是用户有权访问的内容。
3. 先观察并记录页面标题、会话/来源和消息时间；不要批量读取历史消息。
4. 将当前可见消息人工复制到命令参数中运行 Jev gate：

```bash
python experiments/browser-use-jev-ultrafast/field-demo/reply_gate.py \
  --mode live \
  --source "FEISHU/<当前可见页面标题>" \
  --message "<当前可见消息>"
```

5. 只读取输出中的 `decision`、`candidate_template`、`human_confirmation_required`。
6. 对照 `intent / risk / next_action`，确认是否需要人工改写或不回复。
7. 将候选模板人工填入飞书回复框；录下填入前后的页面状态。
8. **停在发送按钮前，不点击发送。**
9. 点击 Finish，保存 trace。

## 必须看到的安全信号

```text
send_allowed: false
human_confirmation_required: true
```

如果输出缺少任一信号，或 Jev 返回异常，禁止填入并停止录制。

## 人工接管

- 登录、验证码、风控、权限提示：停止自动化，用户自行处理。
- Jev 判断为拒绝联系：不要发送任何主动触达内容。
- 意图/风险不确定：保留 `unknown`，不自行补全；交给人工。
- 页面变化或发送按钮状态异常：不点击，保留失败 trace。

## 证据

- bsk trace：打开消息、读取、填入候选、停止前状态。
- Jev gate JSON：只保留来源、判断、候选模板和 `send_allowed=false`；不得保存凭据。

## 停止条件

候选回复已填入且发送按钮仍未点击，即完成本剧本。本剧本不证明真实发送成功，也不替用户决定是否发送。
