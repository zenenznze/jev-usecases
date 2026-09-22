# Field Recording MVP

当前交付不是四站自动化完成，而是让用户以最少步骤开始真实网页录制。

## 最短路径

```bash
cd C:/Users/joe/projects/jev-use
python experiments/browser-use-jev-ultrafast/field-demo/record_ready.py preflight --site feishu
bsk browsers
python experiments/browser-use-jev-ultrafast/field-demo/record_ready.py start --site feishu --script basic --mode live --browser <browser-id>
```

执行输出的 `bsk record start ... --redact-values` 命令后，用户在 Agent Window 中完成 A 剧本。真实网页操作和连续录制由用户掌握；trace bundle 是最终权威证据。

- 录制卡：`RECORDING_CARD.md`
- 分镜：`STORYBOARD.md`
- 站点入口和前置：`sites.json`
- Live/Replay 控制台：`record_console.html`
- 发送前 Jev gate：`reply_gate.py`

## 安全边界

只操作用户已登录且有权访问的可见内容；不绕过登录、验证码、反爬或权限；不批量抓取；不自动发布、交易或发送。遇到登录/验证码/风控/页面不稳定，立即人工接管。
