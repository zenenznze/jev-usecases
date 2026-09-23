---
name: buildsome-fde-publisher
description: >-
  Use when an existing Demo must be added to the Buildsome FDE case gallery and
  published to buildsome.me; triggers include “FDE 案例页新增卡片”, “接入 FDE
  页面做预览”, “链接现成的演示页面”, “把这个 Demo 放到官网”, “上传 Demo 到公网”, “add a demo card”,
  and “publish an existing demo”. Do not use to invent or redesign a Demo from scratch, manage generic
  Astro sites, or change Caddy infrastructure.
---

# Buildsome FDE Demo Publisher

把**已有 Demo**接入 Buildsome 的 FDE 案例展示框架：保留 Demo 自身前端，新增案例卡片、安全验证、经人工发布门后上线公网。

## 适用场景

- 已有 HTML/CSS/JS 或 Astro Demo，需要新增 `/fde-demo/<slug>`。
- 需要在 `/fde-demo` 增加一张整体可点击的案例卡片。
- 需要预览、构建、发布并验证 `buildsome.me` 上的新 Demo。

## 不适用场景

- 从零设计 Demo、重写业务交互或伪造模型能力。
- 通用 Astro/Caddy 运维、域名迁移、服务器初始化。
- Skill 创建、安装或同步；分别交给 `asm-make` 与 `asm`。
- 普通仓库验证、提交和推送；交给 `dev`。

## 前置依赖

- 当前机器能通过 SSH 别名访问目标服务器；默认别名 `lx`。
- 目标仓库默认 `/home/ubuntu/buildsome/buildsome`。
- 站点已有 `src/pages/fde-demo.astro` 和可复用 `demos` 卡片数组。
- Node 版本满足 Astro；当前服务器已验证 Node `v20.20.2`。
- 真正部署前必须取得本次任务明确的人类发布授权。

可覆盖的非敏感环境变量：

```text
BUILDSOME_SSH_HOST=lx
BUILDSOME_REPO=/home/ubuntu/buildsome/buildsome
BUILDSOME_PUBLIC_ORIGIN=https://buildsome.me
```

不得读取或写入 SSH 私钥、API token、Cookie 或 `.env`。

## 输入与输出

**输入：** Demo 源码目录、slug、卡片标题/行业/摘要/能力标签、运行模式（Replay 或 Live）、发布授权状态。

**输出：** Demo 路由与本地资源、FDE 卡片配置、构建与预览证据；获授权后还包括公网 URL、发布快照、健康检查和 Git 交付状态。

## 标准流程

1. **确认边界。** 收集 slug、卡片文案、Demo 入口、资源依赖、Replay/Live 模式和验收 URL。未明确发布授权时只做到暂存预览。
2. **审计目标。** 检查远端规则、Git 状态、`demos` 数组、现有路由和 Caddy 实际 root；保留所有并发改动和未知未跟踪文件。
3. **选择接入方式。** 原生静态包放入 `public/fde-demo/<slug>/`；需要 Astro 组合时使用 `src/pages/fde-demo/<slug>.astro`，资源放 `public/`。不要为了统一官网视觉而改写 Demo 自身前端。
4. **新增卡片。** 只在 `demos` 数组增加一项。整卡必须是链接，卡片内写该 Demo 的 Replay/Live 边界；不要把某个 Demo 的边界声明放在展示页 Hero。
5. **静态安全检查。** Replay 不得包含 `fetch`、XHR、WebSocket、外部 API URL 或真实业务写入；Live 必须准确列出端点、凭据来源和失败边界，且不得把凭据写进仓库。
6. **隔离验证。** 先提交精确文件，再在临时 worktree/复制目录构建和预览。生产 Caddy 直接服务仓库 `dist/`，所以发布授权前**禁止在生产仓库运行 `npm run build`**。
7. **人工验收门。** 给出卡片页和 Demo 预览 URL，等待用户明确批准发布。预览通过、测试通过或 Agent 自报完成都不等于发布授权。
8. **发布。** 先归档当前线上 `dist/`，再把已验证的 staging `dist/` 同步到生产 `dist/`；无需改 Caddy 配置或重启服务。
9. **公网验证。** 检查首页、`/fde-demo/`、Demo、关键 CSS/JS、`www` 域名、Caddy 状态与错误日志；运行 `scripts/verify_public.py`。
10. **Git 交付。** 由 `dev` 精确提交和推送。若 outgoing 范围含未知旧提交或远端认证失败，不得推送并如实报告。

详细命令、卡片模板、staging 与回滚方法见 `references/workflow.md`。

## 错误处理

- **端口或 SSH 隧道失效：**确认远端预览仍为 200，再重建本地转发；不要重复启动多个预览进程。
- **Astro 页面无样式：**动态 JS 注入的 DOM 不会命中 scoped CSS；改用 `<style is:global>` 或外部样式文件。
- **卡片不能整体点击：**外层必须是指向 Demo 的 `<a>`，按钮只能作为视觉子元素。
- **构建会直接上线：**立即停止；生产 `dist/` 是 Caddy live root，改在 staging 构建。
- **Replay 出现网络调用：**阻止发布，删除调用或将模式改为经过明确审查的 Live。
- **公网 308：**使用带尾斜杠的最终 URL 验证，不把正常目录跳转误报为失败。
- **Git push 会夹带旧提交：**不要 push；交付公网不代表有权发布未知 Git 历史。
- **部署后异常：**用发布前归档恢复 `dist/`，再次验证公网和 Caddy 日志。

## 安全与反合理化

| 借口 | 实际边界 |
| --- | --- |
| “只是 build，不算发布” | 在生产仓库 build 会改写 Caddy live root，等同发布。 |
| “Demo 已经能跑，可以顺便改风格” | 接入不授权重设计；保留 Demo 原前端。 |
| “都是静态文件，可以跳过备份” | 错误资源同步同样会让公网不可用。 |
| “先推全部 commits 再说” | 未知 outgoing commit 不属于本任务。 |

出现以下任一情况立即停止：没有明确发布授权、生产构建未备份、Replay 含外部调用、需要读取凭据、需要覆盖并发改动、或公网验证失败。

## 示例触发

- “已有一个销售 Demo，把它加成新的 FDE 卡片并发布到官网。”
- “把这个静态 Demo 上传到公网，入口放在 Buildsome FDE 案例页。”
- “只增加案例卡片和路由，先给我预览，不要发布。”

## 验收标准

- 新卡片整体可点击，文案和模式边界属于该卡片。
- Demo 保留原有视觉，所有资源本地可加载。
- 隔离构建成功；Replay 网络扫描通过或 Live 边界已审查。
- 获授权后公网主域与 `www` 的卡片、Demo、CSS/JS 均返回 200。
- Caddy 健康、无新增错误；发布前快照可定位。
- Git 只包含任务文件，push 状态真实可核验。

## Skill Handoffs

- 创建或修改本技能：load `asm-make` skill。
- 安装、暴露或同步技能：load `asm` skill。
- 仓库验证、提交和推送：load `dev` skill。
