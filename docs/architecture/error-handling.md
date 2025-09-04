# 错误处理策略

## 错误流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API服务器
    participant Service as 业务服务
    participant DB as 数据库

    Client->>API: API请求
    API->>Service: 业务逻辑调用
    Service->>DB: 数据操作
    
    alt 数据库错误
        DB-->>Service: 数据库异常
        Service-->>API: 服务异常
        API-->>Client: 标准化错误响应
    else 业务逻辑错误
        Service-->>API: 业务异常
        API-->>Client: 业务错误响应
    else 成功
        DB-->>Service: 数据返回
        Service-->>API: 业务结果
        API-->>Client: 成功响应
    end
```

## 错误响应格式

```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}
```

---

**由BMAD™核心产品管理框架生成**