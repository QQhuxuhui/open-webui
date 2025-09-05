# Epic 1 部署指南：合规用户管理与内容标识增强

**版本：** 1.0  
**日期：** 2025-01-13  
**框架：** BMAD™ 核心产品管理框架

## 概述

本指南涵盖Epic 1功能的部署，包括SMS验证、内容举报、个人资料管理、实名认证和系统监控。

## 前置条件

### 系统要求

- **Python:** 3.12+
- **数据库:** PostgreSQL 14+
- **缓存:** Redis 6+
- **存储:** 支持加密的文件存储系统
- **内存:** 生产环境最少4GB RAM
- **CPU:** 生产环境最少2核

### 依赖项

```bash
# 核心依赖项（已包含）
flask>=2.3.0
sqlalchemy>=2.0.0
flask-login>=0.6.0
celery>=5.3.0
redis>=4.5.0
pillow>=10.0.0
cryptography>=41.0.0
psutil>=5.9.0

# SMS服务依赖项
alibabacloud-dysmsapi20170525>=3.0.0
tencentcloud-sdk-python>=3.0.0

# 测试依赖项
pytest>=7.4.0
requests>=2.31.0
```

### 环境变量

```bash
# SMS配置
SMS_PROVIDER=alibaba  # 或者 tencent
ALIBABA_ACCESS_KEY_ID=你的访问密钥
ALIBABA_ACCESS_KEY_SECRET=你的密钥
TENCENT_SECRET_ID=你的密钥ID
TENCENT_SECRET_KEY=你的密钥

# 加密配置
VERIFICATION_ENCRYPTION_KEY=你的Fernet密钥

# 文件存储配置
FILE_STORAGE_PATH=/var/uploads
FILE_STORAGE_MAX_SIZE=10485760  # 10MB

# 性能监控配置
ENABLE_PERFORMANCE_MONITORING=true
PERFORMANCE_METRICS_RETENTION_HOURS=168  # 7天
```

## 数据库迁移

### 1. 创建新表

执行以下SQL迁移脚本：

```sql
-- SMS验证表
CREATE TABLE IF NOT EXISTS sms_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) NOT NULL,
    verification_code_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP NULL,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户同意书表
CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL,
    consent_version VARCHAR(20) NOT NULL,
    consented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, consent_type, consent_version)
);

-- 内容举报表
CREATE TABLE IF NOT EXISTS content_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    content_id VARCHAR(255) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    report_category VARCHAR(50) NOT NULL,
    report_reason TEXT,
    content_snapshot JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    moderator_notes TEXT,
    moderator_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 实名认证表
CREATE TABLE IF NOT EXISTS real_name_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    real_name VARCHAR(255) NOT NULL,
    id_type VARCHAR(20) NOT NULL,
    id_number_encrypted TEXT NOT NULL,
    document_front_url VARCHAR(500),
    document_back_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    rejection_reason TEXT,
    verified_at TIMESTAMP NULL,
    verified_by UUID REFERENCES accounts(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
);

-- 个人资料修改日志表
CREATE TABLE IF NOT EXISTS profile_change_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    change_type VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 身份验证令牌表
CREATE TABLE IF NOT EXISTS identity_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    token VARCHAR(128) NOT NULL UNIQUE,
    purpose VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL
);
```

### 2. 创建索引

```sql
-- SMS验证索引
CREATE INDEX idx_sms_verifications_phone_purpose ON sms_verifications(phone_number, purpose);
CREATE INDEX idx_sms_verifications_expires_at ON sms_verifications(expires_at);

-- 用户同意书索引
CREATE INDEX idx_user_consents_user_id ON user_consents(user_id);
CREATE INDEX idx_user_consents_type ON user_consents(consent_type);

-- 内容举报索引
CREATE INDEX idx_content_reports_reporter ON content_reports(reporter_id);
CREATE INDEX idx_content_reports_content ON content_reports(content_id, content_type);
CREATE INDEX idx_content_reports_status ON content_reports(status);
CREATE INDEX idx_content_reports_created_at ON content_reports(created_at);

-- 实名认证索引
CREATE INDEX idx_real_name_verifications_user ON real_name_verifications(user_id);
CREATE INDEX idx_real_name_verifications_status ON real_name_verifications(status);

-- 个人资料修改日志索引
CREATE INDEX idx_profile_change_logs_user_id ON profile_change_logs(user_id);
CREATE INDEX idx_profile_change_logs_created_at ON profile_change_logs(created_at);
CREATE INDEX idx_profile_change_logs_type ON profile_change_logs(change_type);

-- 身份验证令牌索引
CREATE INDEX idx_identity_verification_tokens_user_id ON identity_verification_tokens(user_id);
CREATE INDEX idx_identity_verification_tokens_expires_at ON identity_verification_tokens(expires_at);
```

### 3. 更新用户账户表

```sql
-- 向账户表添加合规相关字段
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name_verified_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS nickname VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
```

## 文件系统设置

### 1. 创建上传目录

```bash
# 创建安全的上传目录
sudo mkdir -p /var/uploads/avatars
sudo mkdir -p /var/uploads/verification_documents
sudo chmod 755 /var/uploads
sudo chmod 750 /var/uploads/verification_documents  # 敏感文档更严格的权限
sudo chown -R app_user:app_group /var/uploads
```

### 2. 配置文件权限

```bash
# 设置适当的文件权限
sudo chmod g+s /var/uploads/avatars
sudo chmod g+s /var/uploads/verification_documents

# 为额外安全创建.htaccess（如果使用Apache）
echo "deny from all" | sudo tee /var/uploads/verification_documents/.htaccess
```

## 应用程序配置

### 1. 更新Flask配置

```python
# config.py 添加内容
SMS_CONFIG = {
    'provider': os.getenv('SMS_PROVIDER', 'alibaba'),
    'rate_limit': {
        'per_phone_per_day': 10,
        'per_ip_per_hour': 20
    },
    'verification_code_length': 6,
    'expiry_minutes': 10
}

VERIFICATION_CONFIG = {
    'encryption_key': os.getenv('VERIFICATION_ENCRYPTION_KEY'),
    'max_pending_days': 90,
    'allowed_file_types': ['jpg', 'jpeg', 'png', 'pdf'],
    'max_file_size_mb': 10
}

PERFORMANCE_CONFIG = {
    'enable_monitoring': os.getenv('ENABLE_PERFORMANCE_MONITORING', 'false').lower() == 'true',
    'metrics_retention_hours': int(os.getenv('PERFORMANCE_METRICS_RETENTION_HOURS', '168')),
    'alert_thresholds': {
        'response_time_ms': 1000,
        'error_rate_percent': 5.0,
        'cpu_percent': 80.0,
        'memory_percent': 85.0
    }
}
```

### 2. 初始化服务

```python
# app.py 添加内容
from services.sms.sms_service import initialize_sms_service
from services.verification_service import verification_service
from services.system_health_service import system_health_service

def create_app():
    app = create_flask_app_with_configs()
    
    # 初始化SMS服务
    initialize_sms_service(app)
    
    # 初始化其他服务
    with app.app_context():
        # 如果不存在则创建数据库表
        from services.profile_service import create_profile_tables
        create_profile_tables()
        
    initialize_extensions(app)
    return app
```

## 部署步骤

### 1. 部署前检查清单

- [ ] 数据库迁移已完成
- [ ] 环境变量已配置
- [ ] 文件存储目录已创建并设置适当权限
- [ ] SMS服务凭证已配置并测试
- [ ] 加密密钥已生成并安全保存
- [ ] 负载均衡器已配置（如适用）
- [ ] 监控系统已准备就绪

### 2. 部署流程

```bash
#!/bin/bash
# deploy_epic1.sh

set -e

echo "开始Epic 1部署..."

# 1. 备份现有数据
pg_dump $DATABASE_URL > backup_pre_epic1_$(date +%Y%m%d_%H%M%S).sql

# 2. 停止应用程序
sudo systemctl stop your-app

# 3. 部署新代码
git pull origin main
pip install -r requirements.txt

# 4. 运行迁移
flask db upgrade

# 5. 运行Epic 1特定设置
python -c "
from app_factory import create_app
from services.profile_service import create_profile_tables
app = create_app()
with app.app_context():
    create_profile_tables()
    print('Epic 1表创建成功')
"

# 6. 测试关键功能
python -m pytest tests/system_tests/test_epic1_integration.py::TestEpic1SystemIntegration::test_system_health_monitoring -v

# 7. 启动应用程序
sudo systemctl start your-app

# 8. 验证部署
sleep 10
curl -f http://localhost:5001/api/health/ping || exit 1

echo "Epic 1部署成功完成！"
```

### 3. 部署后验证

```bash
# 健康检查
curl http://localhost:5001/api/health/status

# 测试SMS服务配置
python -c "
from services.sms.sms_service import SMSService
sms = SMSService()
print(f'SMS提供商: {sms.provider}')
print(f'SMS服务已初始化: {sms.client is not None}')
"

# 测试文件上传目录
ls -la /var/uploads/
touch /var/uploads/avatars/test_write && rm /var/uploads/avatars/test_write
```

## 监控和告警

### 1. 健康检查端点

```bash
# 系统健康
GET /api/health/status

# 性能指标
GET /api/health/metrics

# 历史数据
GET /api/health/metrics/historical?hours=24
```

### 2. 需要监控的关键指标

```yaml
性能指标:
  - 平均响应时间 < 500ms
  - 错误率 < 2%
  - CPU使用率 < 80%
  - 内存使用率 < 85%
  - 磁盘剩余空间 > 5GB

业务指标:
  - SMS验证成功率 > 95%
  - 个人资料更新完成率 > 98%
  - 内容举报处理时间 < 24小时
  - 实名认证处理时间 < 72小时

安全指标:
  - 每IP失败登录尝试 < 10次/小时
  - 检测到的可疑文件上传
  - 数据加密状态: 100%
  - 访问日志异常
```

### 3. 告警规则

```yaml
严重告警:
  - 系统健康状态: 不健康
  - 数据库连接失败
  - 文件存储失败
  - SMS服务失败
  - 错误率 > 5%

警告告警:
  - 响应时间 > 1000ms
  - CPU使用率 > 80%
  - 内存使用率 > 85%
  - 磁盘空间 < 10GB
  - SMS频率限制接近

信息告警:
  - 高流量量
  - 异常用户活动模式
  - 每日/周性能摘要
```

## 安全注意事项

### 1. 数据保护

- **静态加密：** 验证文档和敏感数据加密
- **传输加密：** 所有API通信使用HTTPS
- **访问控制：** 管理功能基于角色的访问控制
- **审计日志：** 所有敏感操作记录IP和用户代理

### 2. SMS安全

- **频率限制：** 防止SMS滥用和成本
- **验证码过期：** 验证码在10分钟内过期
- **尝试限制：** 每个验证码最多5次尝试
- **IP跟踪：** 监控可疑模式

### 3. 文件上传安全

- **文件类型验证：** 仅允许特定的图像/文档类型
- **大小限制：** 防止大文件攻击
- **病毒扫描：** 如需要则实施
- **安全存储：** 验证文档访问受限

## 故障排除

### 常见问题

#### SMS服务不工作
```bash
# 检查SMS提供商配置
python -c "
from services.sms.sms_service import SMSService
sms = SMSService()
print(f'提供商: {sms.provider}')
print(f'客户端已初始化: {sms.client is not None}')
"

# 检查SMS频率限制
redis-cli get "sms_rate_limit:phone:13800138000"
redis-cli get "sms_rate_limit:ip:192.168.1.100"
```

#### 文件上传失败
```bash
# 检查目录权限
ls -la /var/uploads/
id app_user
sudo -u app_user touch /var/uploads/avatars/test_file

# 检查磁盘空间
df -h /var/uploads
```

#### 数据库性能问题
```sql
-- 检查缺失的索引
SELECT schemaname, tablename, attname, inherited, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public' AND tablename IN (
    'sms_verifications', 'content_reports', 'real_name_verifications'
);

-- 检查慢查询
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC
LIMIT 10;
```

### 性能调优

#### 数据库优化
```sql
-- 更新表统计信息
ANALYZE sms_verifications;
ANALYZE content_reports;
ANALYZE real_name_verifications;

-- 检查索引使用情况
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public';
```

#### 缓存优化
```bash
# 检查Redis内存使用情况
redis-cli info memory

# 监控缓存命中率
redis-cli info stats | grep keyspace
```

## 回滚计划

如果部署期间出现问题：

### 1. 紧急回滚

```bash
#!/bin/bash
# rollback_epic1.sh

echo "开始Epic 1回滚..."

# 1. 停止应用程序
sudo systemctl stop your-app

# 2. 恢复之前的代码版本
git checkout previous_stable_tag

# 3. 如需要恢复数据库（小心操作！）
# 仅在数据损坏时使用
# psql $DATABASE_URL < backup_pre_epic1_TIMESTAMP.sql

# 4. 启动应用程序
sudo systemctl start your-app

echo "回滚完成"
```

### 2. 部分回滚

如果只需要禁用特定功能：

```python
# 临时禁用Epic 1功能
EPIC1_FEATURES_ENABLED = False

# 在蓝图注册中
if EPIC1_FEATURES_ENABLED:
    app.register_blueprint(verification_bp)
    app.register_blueprint(health_bp)
```

## 成功标准

部署被认为成功当：

- [ ] 所有健康检查通过
- [ ] SMS验证端到端工作
- [ ] 个人资料管理功能正确
- [ ] 实名认证工作流完成
- [ ] 内容举报系统运行
- [ ] 性能指标在可接受范围内
- [ ] 没有严重安全漏洞
- [ ] 所有集成测试通过
- [ ] 用户验收测试完成

## 支持和维护

### 日常操作

- 监控系统健康仪表板
- 查看性能警报
- 检查SMS使用情况和成本
- 查看安全日志
- 监控错误率

### 周维护

- 查看性能趋势
- 清理过期的验证码
- 归档旧审计日志
- 检查存储使用情况
- 查看用户反馈

### 月任务

- 安全审计查看
- 性能优化查看
- 备份策略验证
- 灾难恢复测试
- 用户体验指标分析

---

**文档版本：** 1.0  
**最后更新：** 2025-01-13  
**下次审查：** 2025-02-13