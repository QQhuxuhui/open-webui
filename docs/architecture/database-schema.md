# 数据库架构

## 数据库架构设计

```sql
-- 扩展现有用户表以支持合规功能
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name_verified_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);

-- 用户协议同意记录表
CREATE TABLE user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(20) NOT NULL CHECK (consent_type IN ('privacy_policy', 'terms_of_service')),
    consent_version VARCHAR(10) NOT NULL,
    consented_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address INET NOT NULL,
    user_agent TEXT NOT NULL,
    
    -- 复合索引用于查询用户的最新同意记录
    UNIQUE(user_id, consent_type, consent_version)
);

-- 短信验证码表
CREATE TABLE sms_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    verification_code_hash VARCHAR(255) NOT NULL, -- 加密存储
    purpose VARCHAR(20) NOT NULL CHECK (purpose IN ('registration', 'login', 'phone_change')),
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 防止暴力破解的索引
    INDEX idx_phone_purpose_created (phone_number, purpose, created_at)
);

-- 内容举报表
CREATE TABLE content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES users(id),
    content_id UUID NOT NULL, -- 引用聊天消息或媒体内容
    content_type VARCHAR(10) NOT NULL CHECK (content_type IN ('text', 'image', 'video')),
    report_category VARCHAR(30) NOT NULL CHECK (
        report_category IN ('inappropriate_content', 'misinformation', 'technical_issue', 'other')
    ),
    report_reason TEXT NOT NULL,
    content_snapshot JSONB NOT NULL, -- 举报时的内容快照
    status VARCHAR(15) DEFAULT 'pending' CHECK (
        status IN ('pending', 'reviewing', 'resolved', 'dismissed')
    ),
    moderator_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- 性能优化索引
    INDEX idx_status_created (status, created_at),
    INDEX idx_reporter_created (reporter_id, created_at),
    INDEX idx_content_type_category (content_type, report_category)
);

-- 实名认证表
CREATE TABLE real_name_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    document_type VARCHAR(20) NOT NULL CHECK (
        document_type IN ('national_id', 'passport', 'drivers_license')
    ),
    document_number_encrypted VARCHAR(500) NOT NULL, -- 加密存储
    document_images TEXT[] NOT NULL, -- S3存储的加密URL数组
    submitted_name VARCHAR(100) NOT NULL,
    verification_status VARCHAR(15) DEFAULT 'pending' CHECK (
        verification_status IN ('pending', 'processing', 'approved', 'rejected', 'expired')
    ),
    verification_notes TEXT,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    expires_at TIMESTAMP, -- 认证有效期
    
    -- 确保用户只能有一个有效的认证记录
    UNIQUE(user_id, verification_status) WHERE verification_status IN ('pending', 'processing', 'approved'),
    INDEX idx_status_submitted (verification_status, submitted_at)
);

-- 扩展聊天消息表以支持AI内容标识
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS ai_generated BOOLEAN DEFAULT FALSE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS ai_model VARCHAR(50);
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS content_labeled BOOLEAN DEFAULT FALSE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS content_watermarked BOOLEAN DEFAULT FALSE;

-- 性能优化索引
CREATE INDEX IF NOT EXISTS idx_chat_messages_ai_generated ON chat_messages(ai_generated, created_at);
CREATE INDEX IF NOT EXISTS idx_users_phone_verified ON users(phone_number, phone_verified) WHERE phone_number IS NOT NULL;
```

---

**由BMAD™核心产品管理框架生成**