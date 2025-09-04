# 项目结构

## 统一项目结构

```plaintext
open-webui-enhanced/
├── .github/                           # CI/CD工作流
│   └── workflows/
│       ├── ci.yml                     # 持续集成流程
│       ├── deploy-staging.yml         # 预发布部署
│       └── deploy-production.yml      # 生产部署
├── apps/                              # 应用包
│   ├── web/                           # Next.js前端应用
│   │   ├── src/
│   │   │   ├── app/                   # Next.js 15 App Router
│   │   │   ├── components/            # React组件
│   │   │   ├── hooks/                 # 自定义React Hooks
│   │   │   ├── services/              # API客户端服务
│   │   │   ├── stores/                # Zustand状态管理
│   │   │   ├── styles/                # 样式文件
│   │   │   └── utils/                 # 前端工具函数
│   │   ├── public/                    # 静态资源
│   │   ├── tests/                     # 前端测试
│   │   └── package.json               # 前端依赖
│   └── api/                           # Flask后端应用
│       ├── src/
│       │   ├── controllers/           # 控制器层
│       │   ├── services/              # 业务逻辑层
│       │   ├── models/                # 数据模型层
│       │   ├── middleware/            # 中间件
│       │   ├── utils/                 # 工具类
│       │   ├── config/                # 配置管理
│       │   └── app.py                 # Flask应用入口
│       ├── migrations/                # 数据库迁移
│       ├── tests/                     # 后端测试
│       ├── requirements.txt           # Python依赖
│       ├── pyproject.toml            # Python项目配置
│       └── Dockerfile                 # Docker镜像定义
├── packages/                          # 共享包
│   ├── shared/                        # 共享类型和工具
│   ├── ui/                            # 共享UI组件库
│   └── config/                        # 共享配置
├── infrastructure/                    # 基础设施即代码
│   ├── aws/                          # AWS CDK定义
│   └── docker/                       # Docker配置
├── scripts/                          # 构建和部署脚本
├── docs/                             # 项目文档
│   ├── prd.md                       # 产品需求文档
│   ├── architecture.md              # 架构文档
│   ├── api/                         # API文档
│   ├── deployment/                  # 部署文档
│   └── development/                 # 开发文档
├── .env.example                     # 环境变量模板
├── .gitignore                       # Git忽略文件
├── package.json                     # 根包配置文件
├── pnpm-workspace.yaml             # PNPM工作空间配置
├── turbo.json                       # Turbo构建配置
└── README.md                        # 项目说明
```

## 开发工作流程

### 本地开发环境设置

#### 前置条件

```bash
# 安装Node.js 18+ 
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 安装PNPM包管理器
npm install -g pnpm

# 安装Python 3.11+
pyenv install 3.11.7
pyenv global 3.11.7

# 安装UV包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装Docker和Docker Compose
# 按照官方文档安装Docker Desktop

# 安装PostgreSQL客户端工具
brew install postgresql  # macOS
# 或 sudo apt-get install postgresql-client  # Ubuntu
```

#### 初始项目设置

```bash
# 克隆项目仓库
git clone https://github.com/your-org/open-webui-enhanced.git
cd open-webui-enhanced

# 安装根依赖
pnpm install

# 设置环境变量
cp .env.example .env.local
# 编辑 .env.local 填入必要配置

# 初始化数据库
pnpm db:setup

# 构建共享包
pnpm build:packages

# 启动开发服务
pnpm dev
```

#### 开发命令

```bash
# 启动所有服务（前端 + 后端 + 数据库）
pnpm dev

# 分别启动服务
pnpm dev:web      # 启动Next.js前端 (http://localhost:3000)
pnpm dev:api      # 启动Flask后端 (http://localhost:5000)
pnpm dev:db       # 启动PostgreSQL和Redis

# 构建命令
pnpm build        # 构建所有包
pnpm build:web    # 构建前端
pnpm build:api    # 构建后端
pnpm build:packages # 构建共享包

# 测试命令
pnpm test         # 运行所有测试
pnpm test:web     # 运行前端测试
pnpm test:api     # 运行后端测试
pnpm test:e2e     # 运行端到端测试

# 代码质量
pnpm lint         # 运行所有linter
pnpm lint:fix     # 修复可自动修复的问题
pnpm type-check   # TypeScript类型检查

# 数据库操作
pnpm db:migrate   # 运行数据库迁移
pnpm db:seed      # 填充测试数据
pnpm db:reset     # 重置数据库
```

### 环境配置管理

#### 环境变量配置

```bash
# 前端环境变量 (apps/web/.env.local)
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:5000
NEXT_PUBLIC_CDN_URL=http://localhost:3000
NEXT_PUBLIC_UPLOAD_MAX_SIZE=10485760  # 10MB

# 后端环境变量 (apps/api/.env)
FLASK_ENV=development
DATABASE_URL=postgresql://user:password@localhost:5432/openwebui_dev
REDIS_URL=redis://localhost:6379/0

# 短信服务配置
SMS_PROVIDER=aws_sns
AWS_SNS_ACCESS_KEY=your-access-key
AWS_SNS_SECRET_KEY=your-secret-key
AWS_SNS_REGION=us-east-1

# JWT配置
JWT_SECRET_KEY=your-super-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1小时

# 文件存储配置
AWS_S3_BUCKET=openwebui-dev-storage
AWS_S3_REGION=us-east-1
```

---

**由BMAD™核心产品管理框架生成**