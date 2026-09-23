# Prior-art Research

检索日期：2026-09-23。查询：`static demo deployment`、`Astro site deployment`、`demo gallery card`、`ssh static site deployment caddy`。

## 本地技能库

未发现覆盖“Buildsome FDE 卡片 + 既有 Demo 接入 + Caddy live dist 发布边界”的技能。`dev` 负责通用仓库交付，不能替代产品特定接入流程。

## 外部候选

| 候选 | 证据 | 决策 |
| --- | --- | --- |
| `astrolicious/agent-skills@astro` | skills.sh 约 15.6K installs；GitHub 仓库活跃；其技能元数据声明 MIT，涵盖通用 Astro 项目与部署。 | **adapt**：借鉴 Astro 页面/静态资源的通用区分；不复制正文。它不了解 Buildsome 卡片契约、生产 `dist` live root 和 Git 边界。 |
| `spillwavesolutions/publishing-astro-websites-agentic-skill@publishing-astro-websites` | skills.sh 约 56 installs；GitHub 仓库近期更新；仓库 API 未发现 license。 | **reject**：用途接近通用 Astro 发布，但缺少可确认许可证，且并非 Buildsome 专用工作流。 |
| `glitternetwork/pinme@pinme-share` | skills.sh 约 487 installs；GitHub 约 3.7K stars、MIT、近期更新。 | **reject**：适合把本地目录上传到 PinMe 分享，不应把 Buildsome 生产发布改成第三方托管。 |
| `render-oss/skills@render-static-sites` | skills.sh 约 306 installs，可信厂商来源。 | **reject**：面向 Render 平台，不符合现有自托管 Caddy 架构。 |

## 决策链

- exact match：无。
- partial/outdated/naming match：无。
- **no_match → 新建** `buildsome-fde-publisher`。

## 原创贡献（invent）

- 把 Buildsome `demos` 卡片契约、整卡点击与边界文案位置固化为项目规则。
- 明确生产仓库 `dist/` 是 Caddy live root，因此“build 即可能发布”，并强制 staging 构建。
- 将发布授权、快照、公网资源验证、Caddy 健康和 unknown outgoing commit 阻断串成一个闭环。
- 保留已有 Demo 自身视觉，不把“接入官网”误解为“重做 Demo 前端”。

未执行任何第三方技能脚本，也未复制第三方技能正文。
