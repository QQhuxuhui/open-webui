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
-- SMS Verification Table
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

-- User Consents Table
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

-- Content Reports Table
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

-- Real Name Verifications Table
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

-- Profile Change Logs Table
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

-- Identity Verification Tokens Table
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

### 2. Create Indexes

```sql
-- SMS Verifications indexes
CREATE INDEX idx_sms_verifications_phone_purpose ON sms_verifications(phone_number, purpose);
CREATE INDEX idx_sms_verifications_expires_at ON sms_verifications(expires_at);

-- User Consents indexes
CREATE INDEX idx_user_consents_user_id ON user_consents(user_id);
CREATE INDEX idx_user_consents_type ON user_consents(consent_type);

-- Content Reports indexes
CREATE INDEX idx_content_reports_reporter ON content_reports(reporter_id);
CREATE INDEX idx_content_reports_content ON content_reports(content_id, content_type);
CREATE INDEX idx_content_reports_status ON content_reports(status);
CREATE INDEX idx_content_reports_created_at ON content_reports(created_at);

-- Real Name Verifications indexes
CREATE INDEX idx_real_name_verifications_user ON real_name_verifications(user_id);
CREATE INDEX idx_real_name_verifications_status ON real_name_verifications(status);

-- Profile Change Logs indexes
CREATE INDEX idx_profile_change_logs_user_id ON profile_change_logs(user_id);
CREATE INDEX idx_profile_change_logs_created_at ON profile_change_logs(created_at);
CREATE INDEX idx_profile_change_logs_type ON profile_change_logs(change_type);

-- Identity Verification Tokens indexes
CREATE INDEX idx_identity_verification_tokens_user_id ON identity_verification_tokens(user_id);
CREATE INDEX idx_identity_verification_tokens_expires_at ON identity_verification_tokens(expires_at);
```

### 3. Update Accounts Table

```sql
-- Add compliance-related fields to accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS real_name_verified_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS nickname VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
```

## File System Setup

### 1. Create Upload Directories

```bash
# Create secure upload directories
sudo mkdir -p /var/uploads/avatars
sudo mkdir -p /var/uploads/verification_documents
sudo chmod 755 /var/uploads
sudo chmod 750 /var/uploads/verification_documents  # More restrictive for sensitive docs
sudo chown -R app_user:app_group /var/uploads
```

### 2. Configure File Permissions

```bash
# Set up proper file permissions
sudo chmod g+s /var/uploads/avatars
sudo chmod g+s /var/uploads/verification_documents

# Create .htaccess for additional security (if using Apache)
echo "deny from all" | sudo tee /var/uploads/verification_documents/.htaccess
```

## Application Configuration

### 1. Update Flask Configuration

```python
# config.py additions
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

### 2. Initialize Services

```python
# app.py additions
from services.sms.sms_service import initialize_sms_service
from services.verification_service import verification_service
from services.system_health_service import system_health_service

def create_app():
    app = create_flask_app_with_configs()
    
    # Initialize SMS service
    initialize_sms_service(app)
    
    # Initialize other services
    with app.app_context():
        # Create database tables if they don't exist
        from services.profile_service import create_profile_tables
        create_profile_tables()
        
    initialize_extensions(app)
    return app
```

## Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] Database migrations completed
- [ ] Environment variables configured
- [ ] File storage directories created with proper permissions
- [ ] SMS service credentials configured and tested
- [ ] Encryption keys generated and secured
- [ ] Load balancer configured (if applicable)
- [ ] Monitoring systems prepared

### 2. Deployment Process

```bash
#!/bin/bash
# deploy_epic1.sh

set -e

echo "Starting Epic 1 deployment..."

# 1. Backup existing data
pg_dump $DATABASE_URL > backup_pre_epic1_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop application
sudo systemctl stop your-app

# 3. Deploy new code
git pull origin main
pip install -r requirements.txt

# 4. Run migrations
flask db upgrade

# 5. Run Epic 1 specific setup
python -c "
from app_factory import create_app
from services.profile_service import create_profile_tables
app = create_app()
with app.app_context():
    create_profile_tables()
    print('Epic 1 tables created successfully')
"

# 6. Test critical functionality
python -m pytest tests/system_tests/test_epic1_integration.py::TestEpic1SystemIntegration::test_system_health_monitoring -v

# 7. Start application
sudo systemctl start your-app

# 8. Verify deployment
sleep 10
curl -f http://localhost:5001/api/health/ping || exit 1

echo "Epic 1 deployment completed successfully!"
```

### 3. Post-Deployment Verification

```bash
# Health check
curl http://localhost:5001/api/health/status

# Test SMS service configuration
python -c "
from services.sms.sms_service import SMSService
sms = SMSService()
print(f'SMS Provider: {sms.provider}')
print(f'SMS Service Initialized: {sms.client is not None}')
"

# Test file upload directories
ls -la /var/uploads/
touch /var/uploads/avatars/test_write && rm /var/uploads/avatars/test_write
```

## Monitoring and Alerting

### 1. Health Check Endpoints

```bash
# System health
GET /api/health/status

# Performance metrics
GET /api/health/metrics

# Historical data
GET /api/health/metrics/historical?hours=24
```

### 2. Key Metrics to Monitor

```yaml
Performance Metrics:
  - Average response time < 500ms
  - Error rate < 2%
  - CPU usage < 80%
  - Memory usage < 85%
  - Disk space > 5GB free

Business Metrics:
  - SMS verification success rate > 95%
  - Profile update completion rate > 98%
  - Content report processing time < 24h
  - Real name verification processing time < 72h

Security Metrics:
  - Failed login attempts per IP < 10/hour
  - Suspicious file uploads detected
  - Data encryption status: 100%
  - Access log anomalies
```

### 3. Alerting Rules

```yaml
Critical Alerts:
  - System health status: unhealthy
  - Database connection failures
  - File storage failures
  - SMS service failures
  - Error rate > 5%

Warning Alerts:
  - Response time > 1000ms
  - CPU usage > 80%
  - Memory usage > 85%
  - Disk space < 10GB
  - SMS rate limit approaching

Info Alerts:
  - High traffic volume
  - Unusual user activity patterns
  - Daily/weekly performance summaries
```

## Security Considerations

### 1. Data Protection

- **Encryption at Rest:** Verification documents and sensitive data encrypted
- **Encryption in Transit:** All API communications use HTTPS
- **Access Control:** Role-based access for admin functions
- **Audit Logging:** All sensitive operations logged with IP and user agent

### 2. SMS Security

- **Rate Limiting:** Prevent SMS abuse and costs
- **Code Expiry:** Verification codes expire within 10 minutes
- **Attempt Limits:** Maximum 5 attempts per code
- **IP Tracking:** Monitor for suspicious patterns

### 3. File Upload Security

- **File Type Validation:** Only allow specific image/document types
- **Size Limits:** Prevent large file attacks
- **Virus Scanning:** Implement if required
- **Secure Storage:** Restricted access to verification documents

## Troubleshooting

### Common Issues

#### SMS Service Not Working
```bash
# Check SMS provider configuration
python -c "
from services.sms.sms_service import SMSService
sms = SMSService()
print(f'Provider: {sms.provider}')
print(f'Client initialized: {sms.client is not None}')
"

# Check SMS rate limiting
redis-cli get "sms_rate_limit:phone:13800138000"
redis-cli get "sms_rate_limit:ip:192.168.1.100"
```

#### File Upload Failures
```bash
# Check directory permissions
ls -la /var/uploads/
id app_user
sudo -u app_user touch /var/uploads/avatars/test_file

# Check disk space
df -h /var/uploads
```

#### Database Performance Issues
```sql
-- Check for missing indexes
SELECT schemaname, tablename, attname, inherited, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public' AND tablename IN (
    'sms_verifications', 'content_reports', 'real_name_verifications'
);

-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC
LIMIT 10;
```

### Performance Tuning

#### Database Optimization
```sql
-- Update table statistics
ANALYZE sms_verifications;
ANALYZE content_reports;
ANALYZE real_name_verifications;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public';
```

#### Cache Optimization
```bash
# Check Redis memory usage
redis-cli info memory

# Monitor cache hit rates
redis-cli info stats | grep keyspace
```

## Rollback Plan

If issues occur during deployment:

### 1. Immediate Rollback

```bash
#!/bin/bash
# rollback_epic1.sh

echo "Starting Epic 1 rollback..."

# 1. Stop application
sudo systemctl stop your-app

# 2. Restore previous code version
git checkout previous_stable_tag

# 3. Restore database if needed (BE CAREFUL!)
# Only if data corruption occurred
# psql $DATABASE_URL < backup_pre_epic1_TIMESTAMP.sql

# 4. Start application
sudo systemctl start your-app

echo "Rollback completed"
```

### 2. Partial Rollback

If only specific features need to be disabled:

```python
# Temporarily disable Epic 1 features
EPIC1_FEATURES_ENABLED = False

# In your blueprint registration
if EPIC1_FEATURES_ENABLED:
    app.register_blueprint(verification_bp)
    app.register_blueprint(health_bp)
```

## Success Criteria

Deployment is considered successful when:

- [ ] All health checks pass
- [ ] SMS verification works end-to-end
- [ ] Profile management functions correctly
- [ ] Real name verification workflow completes
- [ ] Content reporting system operational
- [ ] Performance metrics within acceptable ranges
- [ ] No critical security vulnerabilities
- [ ] All integration tests pass
- [ ] User acceptance testing completed

## Support and Maintenance

### Daily Operations

- Monitor system health dashboard
- Review performance alerts
- Check SMS usage and costs
- Review security logs
- Monitor error rates

### Weekly Maintenance

- Review performance trends
- Clean up expired verification codes
- Archive old audit logs
- Check storage usage
- Review user feedback

### Monthly Tasks

- Security audit review
- Performance optimization review
- Backup strategy verification
- Disaster recovery testing
- User experience metrics analysis

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-13  
**Next Review:** 2025-02-13