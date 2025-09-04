# 数据模型

## 用户（增强）

**目的：** 扩展的用户模型，支持手机验证、实名验证和合规跟踪，同时保持与现有认证的兼容性。

**关键属性：**
- id: string (UUID) - 主标识符（现有）
- email: string | null - 电子邮件地址（现有，现在可选）
- phone_number: string | null - 验证用手机号（新）
- phone_verified: boolean - 手机验证状态（新）
- real_name: string | null - 实名验证的真实姓名（新）
- real_name_verified: boolean - 实名验证状态（新）
- real_name_verified_at: Date | null - 验证时间戳（新）
- nickname: string - 显示名称（增强）
- avatar_url: string | null - 个人资料图片URL（增强）
- created_at: Date - 账户创建时间戳（现有）
- updated_at: Date - 最后个人资料更新（现有）

### TypeScript接口
```typescript
interface User {
  id: string;
  email?: string;
  phone_number?: string;
  phone_verified: boolean;
  real_name?: string;
  real_name_verified: boolean;
  real_name_verified_at?: Date;
  nickname: string;
  avatar_url?: string;
  created_at: Date;
  updated_at: Date;
}
```

### 关系
- 与UserConsent一对多（隐私协议）
- 与ContentReport一对多（提交的举报）
- 与SmsVerification一对多（验证尝试）
- 与ChatMessage一对多（现有，增强）

## UserConsent

**目的：** 跟踪用户对隐私协议和服务条款的同意，具有版本控制用于合规审计。

### TypeScript接口
```typescript
interface UserConsent {
  id: string;
  user_id: string;
  consent_type: 'privacy_policy' | 'terms_of_service';
  consent_version: string;
  consented_at: Date;
  ip_address: string;
  user_agent: string;
}
```

## SmsVerification

**目的：** 管理手机号验证的短信验证码，具有安全和速率限制功能。

### TypeScript接口
```typescript
interface SmsVerification {
  id: string;
  phone_number: string;
  verification_code: string; // 为安全而哈希
  purpose: 'registration' | 'login' | 'phone_change';
  expires_at: Date;
  verified_at?: Date;
  attempts: number;
  max_attempts: number;
  created_at: Date;
}
```

## ContentReport

**目的：** 跟踪用户对AI生成内容的举报和反馈，用于审核和合规目的。

### TypeScript接口
```typescript
interface ContentReport {
  id: string;
  reporter_id: string;
  content_id: string;
  content_type: 'text' | 'image' | 'video';
  report_category: 'inappropriate_content' | 'misinformation' | 'technical_issue' | 'other';
  report_reason: string;
  content_snapshot: {
    content: string;
    ai_model: string;
    timestamp: Date;
    chat_context?: string;
  };
  status: 'pending' | 'reviewing' | 'resolved' | 'dismissed';
  moderator_notes?: string;
  created_at: Date;
  resolved_at?: Date;
}
```

## RealNameVerification

**目的：** 管理监管合规的实名验证文档提交和处理状态。

### TypeScript接口
```typescript
interface RealNameVerification {
  id: string;
  user_id: string;
  document_type: 'national_id' | 'passport' | 'drivers_license';
  document_number: string; // 加密
  document_images: string[];
  submitted_name: string;
  verification_status: 'pending' | 'processing' | 'approved' | 'rejected' | 'expired';
  verification_notes?: string;
  submitted_at: Date;
  processed_at?: Date;
  expires_at?: Date;
}
```

## ChatMessage（增强）

**目的：** 增强的现有聊天消息模型，支持AI内容标识和合规跟踪。

### TypeScript接口
```typescript
interface ChatMessage {
  id: string;
  user_id: string;
  content: string;
  role: 'user' | 'assistant';
  ai_generated: boolean;
  ai_model?: string;
  content_labeled: boolean;
  content_watermarked: boolean;
  created_at: Date;
}
```

---

**由BMAD™核心产品管理框架生成**