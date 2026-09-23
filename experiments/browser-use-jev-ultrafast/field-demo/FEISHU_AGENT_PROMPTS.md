# Feishu 真浏览器自动化：摄像头录制用命令与 Agent 提示词

摄像头由用户自己录制；下面的 Python runner 才是浏览器自动化。它会真实打开/观察/点击/输入 Feishu，动作后重新读取页面；不是人工手点，也不是 CRM fixture。

## 0. 启动

1. 先打开摄像头并开始录制。
2. 确认 Chrome 已登录 Feishu。
3. 在仓库根目录执行下列其中一条命令。

使用真实 Jev 时，子进程需要已有的 `TYPESAFE_API_KEY`；Key 不要写进命令、提示词或录屏。

## A：基础操作

```bash
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario A -Query "项目协作"
```

程序内部实际交给 Agent 的提示词：

```text
在当前已登录的网页版飞书中完成基础操作：使用搜索入口搜索“项目协作”，使用一个当前可见的筛选，打开一个搜索结果详情，再返回结果页。每次动作后重新观察页面，不能使用过时的元素引用。只做导航、搜索、筛选、打开详情和返回；不发送、不发布、不交易、不购买、不付款。满足要求后停止，不要继续探索。
```

## B：可见数据获取

```bash
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario B -Query "项目协作"
```

程序内部实际交给 Agent 的提示词：

```text
在当前已登录的网页版飞书中搜索并打开一个与“项目协作”相关、且当前用户有权访问的详情页。只读取页面当前可见内容，提取可见的标题、来源、时间和状态，结构化输出来源与字段；不要批量滚动、批量抓取、调用隐藏接口或读取权限外内容。每次动作后重新观察页面。不要发送、发布、交易、购买或付款；找到详情并完成可见数据读取后停止。
```

`--allow-visible-data` 会把当前页面读取到的最多 80 行可见文本结构化输出到终端和本地 evidence；不要在敏感页面使用。

## C：实时回复，停在发送前

```bash
powershell -ExecutionPolicy Bypass -File experiments/browser-use-jev-ultrafast/field-demo/run_feishu_live.ps1 -Scenario C
```

程序内部实际交给 Agent 的提示词：

```text
在当前已登录的网页版飞书中打开消息入口，找到一条最新的可见新消息并打开会话详情。只读取当前页面真实可见消息，然后调用 Jev 判断消息意图、回复风险和下一动作，生成候选回复或安全模板。将候选回复自动填入当前页面的回复输入框，填入后重新观察并确认输入框确实包含候选内容。绝对不要点击发送、发布、交易、购买或付款按钮；完成填入后立即停止，等待人工确认。
```

C 的自动化边界：

```text
浏览器读取真实消息：程序完成
Jev 判断意图/风险/下一动作：程序完成
候选回复填入网页输入框：程序完成
发送：程序禁止，停在发送前
```

## 失败停止

- 登录页、验证码、风控页：程序停止，用户人工处理。
- 找不到稳定控件：程序停止，不猜 selector、不重复点击。
- Jev 或页面读取失败：保留 evidence，程序不发送。
- 录屏看到发送按钮：这是停止点，不要让程序继续。
