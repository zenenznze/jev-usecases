# Buildsome FDE 接入与发布工作流

仅在 `SKILL.md` 的标准流程需要具体命令时读取本文。

## 1. 参数与目标

```bash
HOST="${BUILDSOME_SSH_HOST:-lx}"
REPO="${BUILDSOME_REPO:-/home/ubuntu/buildsome/buildsome}"
ORIGIN="${BUILDSOME_PUBLIC_ORIGIN:-https://buildsome.me}"
SLUG="<kebab-case-slug>"
```

先记录：Demo 源目录、入口文件、标题、行业、摘要、能力标签、Replay/Live 模式、是否已授权发布。

## 2. 远端只读审计

```bash
ssh "$HOST" "cd '$REPO' && git status --short --branch && git log -8 --oneline"
ssh "$HOST" "python3 - <<'PY'
import json, urllib.request
cfg=json.load(urllib.request.urlopen('http://127.0.0.1:2019/config/', timeout=5))
print(json.dumps(cfg, ensure_ascii=False)[:12000])
PY"
```

确认 Caddy root 是否仍为 `$REPO/dist`。如果不是，停止套用本文中的发布命令，按实际配置重新规划。

不要读取仓库中的 `.env`、认证配置、私钥或用户数据目录。

## 3. 接入形态

### 原生静态 Demo

保持源码结构，目标为：

```text
public/fde-demo/<slug>/index.html
public/fde-demo/<slug>/assets/...
```

所有资源使用相对路径或站内绝对路径。不要保留开发服务器 URL。

### Astro Demo

目标为：

```text
src/pages/fde-demo/<slug>.astro
public/fde-demo/<slug>/...
```

如果页面内容由外部 JavaScript 动态插入，Astro scoped CSS 无法自动覆盖这些节点。使用 `<style is:global>` 或独立 CSS，并在构建产物中确认选择器未带 `data-astro-*` 作用域。

## 4. 卡片模板

`src/pages/fde-demo.astro` 已有 `demos` 数组。增加一项，不复制页面框架：

```ts
{
  sector: "<行业 · 场景>",
  title: "<Demo 标题>",
  summary: "<业务问题与门禁价值>",
  capabilities: ["<能力一>", "<能力二>", "<能力三>"],
  href: "/fde-demo/<slug>",
  status: "可交互 Replay",
  boundary: "纯静态 Replay · 使用固定演示数据，不调用外部 API。",
}
```

若是 Live，必须把 `status` 和 `boundary` 改成真实描述。不要声称调用模型、CRM 写入或预约成功，除非该行为确实发生且可核验。

卡片渲染必须继续满足：

- 外层 `<a class="demo-card-link">` 包住整张 `<article>`；
- CTA 是卡片内的视觉元素，不是唯一点击区域；
- 当前导航不单独加粗或改变静止颜色；
- Demo 边界描述位于卡片和 Demo 内，不放进展示页 Hero。

## 5. 隔离构建与预览

生产仓库的 `dist/` 是 live root。发布前不要在那里 build。

推荐在任务提交后创建临时 worktree：

```bash
TASK_COMMIT="$(ssh "$HOST" "cd '$REPO' && git rev-parse HEAD")"
STAGE="/tmp/buildsome-fde-${SLUG}-$(date +%s)"
ssh "$HOST" "cd '$REPO' && git worktree add --detach '$STAGE' '$TASK_COMMIT'"
ssh "$HOST" "ln -s '$REPO/node_modules' '$STAGE/node_modules'"
ssh "$HOST" "cd '$STAGE' && export PATH=\"\$HOME/.nvm/versions/node/v20.20.2/bin:\$PATH\" && npm run build"
ssh "$HOST" "cd '$STAGE' && setsid npm run preview -- --port <free-port> </dev/null >'/tmp/${SLUG}-preview.log' 2>&1 &"
```

如果任务文件尚未提交，先由 `dev` 精确提交。不要用 stash、reset 或复制整个脏工作树来绕过隔离。

验证后记录 staging 路径、端口和进程；清理前确认用户不再需要预览。

## 6. 确定性检查

在有目标仓库副本的机器上：

```bash
python .agents/skills/buildsome-fde-publisher/scripts/validate_fde_integration.py \
  --repo <buildsome-repo-or-stage> --slug "$SLUG" --title "<Demo 标题>" --mode replay
```

Replay 模式检查目标 Demo 文件中的网络原语和外部 URL。它是发布门的一部分，不替代人工检查动态依赖。

## 7. 发布门与备份

只有用户明确说“发布、部署、上线”后执行。

```bash
STAMP="$(date +%Y%m%d-%H%M%S)"
ssh "$HOST" "mkdir -p /home/ubuntu/buildsome/releases && tar -C '$REPO' -czf '/home/ubuntu/buildsome/releases/buildsome-pre-${SLUG}-${STAMP}.tar.gz' dist"
```

验证归档存在且可读，然后把**已验证的 staging 产物**同步到 live root：

```bash
ssh "$HOST" "rsync -a --delete '$STAGE/dist/' '$REPO/dist/'"
```

如果没有 `rsync`，停止并设计同文件系统的安全替换；不要临时用 `rm -rf dist`。

Caddy 直接读取 `dist/`，通常不需要 reload 或 restart。

## 8. 公网验证

```bash
python .agents/skills/buildsome-fde-publisher/scripts/verify_public.py \
  --origin "$ORIGIN" --slug "$SLUG" --title "<Demo 标题>" --check-www
```

服务器健康：

```bash
ssh "$HOST" "systemctl is-active caddy && journalctl -u caddy --since '10 minutes ago' --no-pager -p err"
```

目录路由可能把无尾斜杠 URL 以 308 跳转到带尾斜杠 URL；验证最终 200 即可。

## 9. 回滚

公网静态资源或页面验证失败时，立即停止后续动作，定位发布前归档：

```bash
ssh "$HOST" "ls -lt /home/ubuntu/buildsome/releases/buildsome-pre-${SLUG}-*.tar.gz | head"
```

恢复必须先把当前失败版本另存为故障证据，再从选定归档恢复到临时目录并同步至 `dist/`。不要直接在归档上猜测或覆盖唯一副本。恢复后重复公网与 Caddy 健康检查。

## 10. Git 边界

部署成功不等于 Git 可推送。检查完整 `origin/main..HEAD`：

- 每个 outgoing commit 都属于已确认交付范围，且远端认证有效：由 `dev` 推送并验证远端 SHA。
- 存在旧提交、未知提交、并发任务提交或认证失败：不推送，报告准确 blocker。

永不 force-push、reset、stash、pull 或覆盖未知文件。
