# Feishu B：可见数据读取录制脚本（LIVE）

**目标：** 读取当前屏幕可见且用户有权访问的信息，结构化记录来源；不批量抓取、不导出权限外内容。

## 启动

```bash
bsk browsers
python experiments/browser-use-jev-ultrafast/field-demo/start_recording.py \
  --script data --mode live --browser <browser-id> --run
```

## 逐步动作

1. 打开飞书首页，确认登录态正常；遇到登录/验证码/风控立即停止。
2. 搜索一个你有权访问的目标文档或会话，并打开详情。
3. 只读取当前可见区域，不为获取更多数据而连续翻页、批量滚动或调用隐藏接口。
4. 将以下字段手工记录到本地笔记或 `record_console.html` 的证据区：

```text
source: FEISHU/<页面标题或可见来源>
title: <当前可见标题>
time: <当前可见时间；无则填 unknown>
status: <当前可见状态；无则填 unknown>
observed_at: <本地时间>
```

5. 回到详情页，核对来源和标题仍可见；不修改页面内容。
6. 点击 Finish 停止录制。

## 观察点

- 每个字段都能在当前可见页面中指认位置。
- `unknown` 必须保留，不能用猜测补齐。
- 来源页面/标题要和结构化记录同时保留。
- 不记录密码、验证码、Cookie、Token、私密字段或权限外字段。

## 证据

- bsk trace 的导航、搜索、详情和停止动作。
- 结构化记录的来源字段。
- 页面截图/observe 仅在用户确认不含敏感信息时保留。

## 停止条件

字段记录完成即停止。发生权限提示、验证码、反爬或页面不稳定，保留失败 trace 并人工接管。
