# 技术栈

## 技术栈表

| 类别 | 技术 | 版本 | 用途 | 理由 |
|------|------|------|------|------|
| 前端语言 | TypeScript | 5.0+ | 类型安全的前端开发 | 现有选择，提供优秀的开发体验和编译时错误检测 |
| 前端框架 | Next.js | 15.x | 基于React的全栈框架 | 当前框架，优秀的SSR/SSG支持，内置优化 |
| UI组件库 | shadcn/ui + Radix UI | Latest | 可访问、可定制的组件 | 现代无头组件，完美适合合规UI需求 |
| 状态管理 | Zustand | 4.4+ | 轻量级状态管理 | 新合规功能的简单高性能Redux替代方案 |
| 后端语言 | Python | 3.11+ | 服务端开发 | 当前语言，丰富的AI/ML集成生态系统 |
| 后端框架 | Flask | 3.0+ | 轻量级Python Web框架 | 当前框架，成熟生态系统，易于扩展 |
| API样式 | REST with OpenAPI | OpenAPI 3.1 | 带文档的RESTful API | 与现有模式一致，优秀的工具支持 |
| 数据库 | PostgreSQL | 15+ | 主要关系数据库 | 健壮、ACID兼容，优秀的JSON支持用于灵活模式 |
| 缓存 | Redis | 7.0+ | 会话和数据缓存 | 高性能，支持复杂数据结构 |
| 文件存储 | AWS S3 | Latest | 文档和媒体存储 | 可扩展、安全、合规就绪的加密 |
| 认证 | JWT + Flask-Login | Latest | 用户认证和会话 | 通过无状态API令牌扩展现有认证 |
| 前端测试 | Vitest + Testing Library | Latest | 前端单元和集成测试 | 快速、现代的测试，优秀的React支持 |
| 后端测试 | pytest + pytest-asyncio | Latest | 后端单元和集成测试 | 当前测试框架，成熟的Python生态系统 |
| E2E测试 | Playwright | Latest | 端到端测试 | 合规工作流程的跨浏览器测试 |
| 构建工具 | Vite | 5.0+ | 前端构建和开发服务器 | 快速、现代的构建工具，优秀的Next.js集成 |
| 打包工具 | Webpack (via Next.js) | Latest | JavaScript打包 | Next.js内置，生产优化 |
| IaC工具 | Docker Compose + AWS CDK | Latest | 基础设施即代码 | 保持当前Docker方法，添加AWS基础设施 |
| CI/CD | GitHub Actions | Latest | 自动化测试和部署 | 与现有开发工作流程优秀集成 |
| 监控 | AWS CloudWatch + Sentry | Latest | 应用程序和错误监控 | 综合监控与错误跟踪 |
| 日志 | Python logging + Winston.js | Latest | 结构化应用程序日志 | 前端和后端一致的日志记录 |
| CSS框架 | Tailwind CSS | 3.4+ | 实用优先的CSS框架 | 与组件库优秀配合，快速开发 |

## 其他合规特定技术

| 类别 | 技术 | 版本 | 用途 | 理由 |
|------|------|------|------|------|
| 短信服务 | AWS SNS | Latest | 短信验证传递 | 可靠、全球覆盖、合规就绪 |
| 短信备用 | 腾讯云短信 | Latest | 中国市场短信传递 | 区域合规和可靠性 |
| 图像处理 | Sharp | Latest | 图像水印和处理 | 高性能、优秀的Node.js集成 |
| 视频处理 | FFmpeg (via fluent-ffmpeg) | Latest | 视频水印 | 行业标准、全面格式支持 |
| 实时功能 | Socket.io | 4.7+ | 实时内容标识 | 成熟的WebSocket库，具有回退支持 |
| 数据验证 | Zod | Latest | 运行时类型验证 | 前端和后端的类型安全验证 |
| API文档 | Swagger UI | Latest | 交互式API文档 | 从OpenAPI规范自动生成 |

---

**由BMAD™核心产品管理框架生成**