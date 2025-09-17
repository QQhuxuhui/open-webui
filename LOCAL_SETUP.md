# 汉云WebUI本地开发环境搭建指南

## 📋 环境要求

### 系统要求
- **操作系统**: Linux/macOS/Windows WSL2
- **Node.js**: 18.13.0 - 22.x.x
- **Python**: 3.11 - 3.12
- **包管理器**: npm >= 6.0.0

### 依赖工具
- **Node.js版本管理**: nvm
- **Python环境管理**: conda (推荐) 或 venv
- **容器工具**: Docker (可选，用于数据库等服务)

## 🚀 快速启动

### 第一步：环境准备

#### 1.1 确认工具版本
```bash
# 检查Node.js版本
node --version  # 应该在 18.13.0 - 22.x.x 范围

# 检查Python版本
python --version  # 应该是 3.11 或 3.12

# 检查conda
conda --version
```

#### 1.2 配置Node.js环境
```bash
# 加载nvm环境
source ~/.nvm/nvm.sh

# 安装并使用推荐的Node.js版本
nvm install 20.18.3
nvm use 20.18.3

# 验证版本
node --version
npm --version
```

### 第二步：前端启动

#### 2.1 进入项目目录
```bash
cd /usr/src/workspace/github/QQhuxuhui/open-webui
```

#### 2.2 清理并安装依赖
```bash
# 清理之前的安装（如果有）
rm -rf node_modules package-lock.json
npm cache clean --force

# 安装依赖
npm install

# 如果遇到依赖冲突，使用兼容模式
# npm install --legacy-peer-deps
```

#### 2.3 准备前端资源
```bash
# 获取Pyodide资源（AI功能需要）
npm run pyodide:fetch
```

#### 2.4 启动前端开发服务器
```bash
# 启动开发服务器
npm run dev

# 或指定端口启动
# npm run dev:5050
```

**前端访问地址**: http://localhost:5173

### 第三步：后端启动

#### 3.1 创建Python虚拟环境
```bash
# 使用conda创建虚拟环境（推荐）
conda create -n open-webui python=3.11
conda activate open-webui

# 或使用venv
# python -m venv venv
# source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows
```

#### 3.2 安装后端依赖
```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 返回项目根目录
cd ..
```

#### 3.3 启动后端服务
```bash
# 进入后端目录
cd backend

# 给启动脚本执行权限
chmod +x start.sh

# 启动后端服务
./start.sh
```

**后端访问地址**:
- API接口: http://localhost:8080
- API文档: http://localhost:8080/docs

## 🔧 详细配置说明

### 环境变量配置

在项目根目录创建 `.env` 文件：

```bash
# 创建环境配置
cat > .env << 'EOF'
# 应用配置
WEBUI_NAME="汉云WebUI"
ENV=dev
WEBUI_AUTH=True

# 数据库配置
DATABASE_URL=sqlite:///./webui.db

# 安全配置（自动生成）
# WEBUI_SECRET_KEY 会由启动脚本自动生成

# 开发配置
WEBUI_URL=http://localhost:3000
DEBUG=True

# AI服务配置（可选）
ENABLE_OLLAMA_API=true
OLLAMA_BASE_URL=http://localhost:11434

# 功能开关
ENABLE_SIGNUP=true
ENABLE_LOGIN_FORM=true
ENABLE_API_KEY=true
EOF
```

### 端口配置

#### 默认端口
- **前端**: 5173 (Vite开发服务器)
- **后端**: 8080 (FastAPI服务器)

#### 修改端口
```bash
# 前端端口修改
npm run dev -- --port 3000

# 后端端口修改（修改backend/start.sh中的PORT变量）
export PORT=8000
```

## 🛠️ 开发工具配置

### 代码质量工具

```bash
# 前端代码检查
npm run lint          # ESLint检查
npm run format        # Prettier格式化
npm run check         # Svelte类型检查

# 后端代码检查
npm run lint:backend   # Pylint检查
npm run format:backend # Black格式化
```

### 测试运行

```bash
# 前端测试
npm run test:frontend

# 类型检查
npm run check:watch   # 监听模式
```

## 🐛 常见问题解决

### 问题1：npm install失败

**症状**: 依赖版本冲突
```
npm error ERESOLVE could not resolve
```

**解决方案**:
```bash
# 清理缓存
rm -rf node_modules package-lock.json
npm cache clean --force

# 使用兼容模式安装
npm install --legacy-peer-deps
```

### 问题2：端口被占用

**症状**:
```
Error: listen EADDRINUSE: address already in use :::5173
```

**解决方案**:
```bash
# 查找占用进程
lsof -ti:5173
lsof -ti:8080

# 杀死进程
kill $(lsof -ti:5173)
kill $(lsof -ti:8080)

# 或使用其他端口
npm run dev -- --port 3000
```

### 问题3：Python虚拟环境问题

**症状**: pip install失败或Python模块找不到

**解决方案**:
```bash
# 确认虚拟环境激活
conda activate open-webui
which python  # 应该指向conda环境

# 重新安装依赖
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 问题4：数据库连接问题

**症状**: 数据库相关错误

**解决方案**:
```bash
# 删除现有数据库文件重新初始化
rm -f webui.db
rm -f backend/webui.db

# 重启后端服务
```

### 问题5：权限问题

**症状**: Permission denied

**解决方案**:
```bash
# 修复文件权限
sudo chown -R $USER:$USER .
chmod +x backend/start.sh
chmod +x dev-start.sh
```

## 📊 服务状态检查

### 健康检查脚本

创建检查脚本 `check-services.sh`:

```bash
#!/bin/bash

echo "🔍 检查服务状态..."

# 检查前端服务
if curl -s http://localhost:5173 > /dev/null; then
    echo "✅ 前端服务运行正常 (http://localhost:5173)"
else
    echo "❌ 前端服务未运行"
fi

# 检查后端API
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ 后端API运行正常 (http://localhost:8080)"
else
    echo "❌ 后端API未运行"
fi

# 检查API文档
if curl -s http://localhost:8080/docs > /dev/null; then
    echo "✅ API文档可访问 (http://localhost:8080/docs)"
else
    echo "❌ API文档不可访问"
fi

echo "🏁 检查完成"
```

```bash
# 给脚本执行权限并运行
chmod +x check-services.sh
./check-services.sh
```

## 🚀 生产环境部署

### 构建生产版本

```bash
# 构建前端
npm run build

# 预览构建结果
npm run preview
```

### 使用Docker部署

```bash
# 构建Docker镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📝 开发流程建议

### 1. 开发环境启动顺序
```bash
# 终端1: 启动后端
cd backend && ./start.sh

# 终端2: 启动前端
npm run dev

# 终端3: 开发工具（可选）
npm run check:watch
```

### 2. 代码提交前检查
```bash
# 运行所有检查
npm run lint
npm run check
npm run format

# 确保服务正常
./check-services.sh
```

### 3. 功能测试流程
1. 访问前端界面: http://localhost:5173
2. 检查API文档: http://localhost:8080/docs
3. 测试核心功能：注册、登录、对话等

---

## 📞 技术支持

如果遇到其他问题：

1. **查看日志**: 检查终端输出的错误信息
2. **重启服务**: 按Ctrl+C停止，重新运行启动命令
3. **清理重装**: 删除node_modules和虚拟环境，重新安装
4. **检查版本**: 确认Node.js和Python版本符合要求

**最后更新**: 2025-09-17
**适用版本**: 汉云WebUI v0.6.26