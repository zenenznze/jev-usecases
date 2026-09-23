# Feishu 真浏览器自动化录制卡

摄像头由用户录制；浏览器由 `run_feishu_browser.py` 自动控制。不要运行 `bsk record`，不要人工代替程序点击。

## 启动

```bash
cd C:/Users/joe/projects/jev-use
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario A -Query "项目协作"
```

先开摄像头，再运行命令。程序打开并操作真实 Feishu 页面；摄像头记录浏览器画面。

## A 基础操作

Agent 目标：搜索“项目协作”→可见筛选→打开详情→返回。动作后重新观察；不发送、不发布、不交易。

## B 数据获取

```bash
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario B -Query "项目协作"
```

Agent 自动打开有权访问的详情页，读取当前可见标题、来源、时间、状态，结构化输出；不批量滚动/抓取。

## C 实时回复

```bash
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario C
```

Agent 自动打开真实新消息→读取页面→调用 Jev→生成候选回复→填入回复框→重新读取确认。发送按钮永远不点击，停在人工确认前。

完整提示词：`FEISHU_AGENT_PROMPTS.md`；User scope key 注入 wrapper：`run_feishu_live.ps1`

## 停止条件

登录/验证码/风控/页面变化/控件不稳定/Je​​v失败时停止。A/B/C 完成各自目标后立即停止；不继续探索。
