# Intent Card

- **Job:** 把已有 Demo 接入 Buildsome FDE 案例框架，新增整体可点击卡片，并在明确授权后安全发布到公网。
- **用户:** 当前项目中的 Joe 与负责 Buildsome FDE 交付的 Agent。
- **输入:** Demo 源码、slug、卡片元数据、Replay/Live 模式、目标服务器可达性和发布授权。
- **输出:** Demo 路由/资源、案例卡片、隔离构建与预览证据；发布后提供公网 URL、快照、健康与 Git 状态。
- **排除项:** 从零设计 Demo、通用 Astro/Caddy 运维、凭据管理、Skill 安装同步、无边界的仓库交付。
- **约束:** 技能实体安装在当前项目 `.agents/skills/buildsome-fde-publisher/`，不用软链接；默认通过 `ssh lx` 操作 `/home/ubuntu/buildsome/buildsome`；生产 Caddy 直接服务 `dist/`；不读取凭据；保留并发改动；部署必须有人类授权。
- **成功标准:** 卡片和 Demo 在隔离环境通过验证；获授权后主域及 www 页面/资源返回 200，Caddy 健康，有发布前快照；Git 交付不夹带未知提交。
- **Archetype:** governed。理由：包含 SSH、生产发布、网络验证和回滚边界。

## 用户原话触发词

- “假设我们已有一个Demo的代码，然后把它上传到公网”
- “新增卡片的部分”
- “做成一个项目级别的技能”
- “本机当前工作目录安装，不是vps”
- “不需要用软链接的形式，直接安装”
