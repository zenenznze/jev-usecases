# Field Recording MVP

摄像头由用户录制；`run_feishu_browser.py` 是真正的浏览器自动化。它使用上游 `jev_ultrafast.Agent + Browser`，由实时 Jev 根据页面观察选择动作，动作后重新观察；不使用 CRM fixture。

## 最短路径

```bash
cd C:/Users/joe/projects/jev-use
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario A -Query "项目协作"
```

先开摄像头，再运行命令。程序会自动控制 Feishu 浏览器；用户只观察。A/B/C 的完整 Agent 提示词和命令在 `FEISHU_AGENT_PROMPTS.md`。

- 真实自动化 runner：`run_feishu_browser.py`
- 可复制的命令与 Agent 提示词：`FEISHU_AGENT_PROMPTS.md`
- 最小连接检查：`record_ready.py preflight --site feishu`
- 站点入口和前置：`sites.json`

## 三个自动化边界

- A：自动导航、搜索、筛选、打开详情、返回。
- B：自动读取当前可见页面内容并结构化输出来源/字段。
- C：自动读取真实消息、调用 Jev 判断、自动填入候选回复；自动化硬阻止发送。

只操作用户已登录且有权访问的可见内容；不绕过登录、验证码、反爬或权限；不批量抓取；不自动发布、交易或发送。