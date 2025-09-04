# 后端架构

## 服务架构

### 传统服务器架构组织

```
api/src/
├── controllers/               # 控制器层（路由处理）
│   ├── __init__.py
│   ├── auth_controller.py     # 认证相关路由
│   ├── profile_controller.py  # 用户资料路由
│   ├── content_controller.py  # 内容相关路由
│   ├── chat_controller.py     # 聊天路由（扩展现有）
│   └── admin_controller.py    # 管理员路由
├── services/                  # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py        # 认证业务逻辑
│   ├── sms_service.py         # 短信服务
│   ├── profile_service.py     # 用户资料服务
│   ├── content_service.py     # 内容处理服务
│   ├── report_service.py      # 举报处理服务
│   ├── verification_service.py # 实名认证服务
│   └── notification_service.py # 通知服务
├── models/                    # 数据模型层
│   ├── __init__.py
│   ├── user.py               # 用户模型（扩展现有）
│   ├── user_consent.py       # 用户协议同意模型
│   ├── sms_verification.py   # 短信验证模型
│   ├── content_report.py     # 内容举报模型
│   ├── real_name_verification.py # 实名认证模型
│   └── chat_message.py       # 聊天消息模型（扩展现有）
├── middleware/               # 中间件
│   ├── __init__.py
│   ├── auth_middleware.py    # 认证中间件
│   ├── rate_limit_middleware.py # 频率限制中间件
│   ├── content_label_middleware.py # 内容标识中间件
│   └── audit_middleware.py   # 审计日志中间件
├── utils/                    # 工具类
│   ├── __init__.py
│   ├── encryption.py        # 加密工具
│   ├── validation.py        # 数据验证
│   ├── file_handler.py      # 文件处理
│   └── error_handler.py     # 错误处理
└── app.py                   # Flask应用入口
```

---

**由BMAD™核心产品管理框架生成**