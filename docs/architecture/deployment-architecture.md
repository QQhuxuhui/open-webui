# 部署架构

## 部署策略

**前端部署：**
- **平台：** Vercel (推荐) 或 AWS CloudFront + S3
- **构建命令：** `pnpm build:web`
- **输出目录：** `apps/web/.next`
- **CDN/Edge：** 全球CDN加速，边缘函数支持

**后端部署：**
- **平台：** AWS ECS Fargate 或 AWS Lambda
- **构建命令：** Docker镜像构建
- **部署方式：** 蓝绿部署，零停机更新

## 环境配置

| 环境 | 前端URL | 后端URL | 用途 |
|------|---------|---------|------|
| Development | http://localhost:3000 | http://localhost:5000 | 本地开发环境 |
| Staging | https://staging.openwebui.com | https://api-staging.openwebui.com | 预发布测试环境 |
| Production | https://openwebui.com | https://api.openwebui.com | 生产环境 |

---

**由BMAD™核心产品管理框架生成**