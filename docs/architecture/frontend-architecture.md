# 前端架构

## 组件架构

### 组件组织结构

```
apps/web/src/
├── components/
│   ├── ui/                     # shadcn/ui基础组件
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── modal.tsx
│   │   └── form.tsx
│   ├── auth/                   # 认证相关组件
│   │   ├── PhoneRegister.tsx   # 手机注册组件
│   │   ├── PhoneLogin.tsx      # 手机登录组件
│   │   ├── SMSVerification.tsx # 短信验证组件
│   │   └── ConsentCheckbox.tsx # 协议同意组件
│   ├── chat/                   # 聊天界面组件（扩展现有）
│   │   ├── ChatMessage.tsx     # 增强的消息组件
│   │   ├── AIContentLabel.tsx  # AI内容标识组件
│   │   ├── ContentReport.tsx   # 内容举报组件
│   │   └── MediaWatermark.tsx  # 媒体水印组件
│   ├── profile/                # 用户资料管理组件
│   │   ├── ProfileEditor.tsx   # 资料编辑组件
│   │   ├── RealNameVerify.tsx  # 实名认证组件
│   │   ├── PhoneChange.tsx     # 手机号修改组件
│   │   └── AvatarUpload.tsx    # 头像上传组件
│   └── common/                 # 通用组件
│       ├── Layout.tsx          # 页面布局组件
│       ├── Header.tsx          # 页面头部组件
│       └── LoadingSpinner.tsx  # 加载动画组件
```

## 状态管理架构

```typescript
// Zustand状态管理结构
interface ComplianceState {
  // 用户认证状态
  auth: {
    isAuthenticated: boolean;
    user: User | null;
    phoneVerificationStep: 'phone' | 'code' | 'complete';
    registrationConsents: {
      privacy: boolean;
      terms: boolean;
    };
  };
  
  // 用户资料状态
  profile: {
    editMode: boolean;
    verificationStatus: {
      phone: boolean;
      realName: 'none' | 'pending' | 'approved' | 'rejected';
    };
    uploadProgress: number;
  };
  
  // 内容合规状态
  content: {
    aiLabelsEnabled: boolean;
    reportModalOpen: boolean;
    selectedContent: string | null;
    watermarkSettings: {
      position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
      opacity: number;
    };
  };
}
```

## 路由架构

```
apps/web/src/app/
├── (auth)/                     # 认证相关路由组
│   ├── login/
│   │   └── page.tsx           # 登录页面
│   ├── register/
│   │   └── page.tsx           # 注册页面
│   └── phone-verify/
│       └── page.tsx           # 手机验证页面
├── (dashboard)/               # 主要功能路由组
│   ├── chat/
│   │   ├── page.tsx           # 聊天主页面
│   │   └── [id]/
│   │       └── page.tsx       # 特定对话页面
│   ├── profile/
│   │   ├── page.tsx           # 用户资料页面
│   │   ├── edit/
│   │   │   └── page.tsx       # 资料编辑页面
│   │   └── verify/
│   │       └── page.tsx       # 实名认证页面
│   └── reports/
│       ├── page.tsx           # 举报历史页面
│       └── [id]/
│           └── page.tsx       # 举报详情页面
```

---

**由BMAD™核心产品管理框架生成**