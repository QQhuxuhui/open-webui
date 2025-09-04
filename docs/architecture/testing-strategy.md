# 测试策略

## 测试金字塔

```
        E2E Tests (10%)
       /            \
   Integration Tests (20%)
  /                    \
Frontend Unit (35%)  Backend Unit (35%)
```

## 测试组织

**前端测试结构：**
```
apps/web/tests/
├── components/          # 组件单元测试
│   ├── auth/
│   ├── chat/
│   └── profile/
├── services/           # 服务层测试
├── hooks/              # 自定义Hook测试
├── integration/        # 集成测试
└── setup.ts           # 测试配置
```

**后端测试结构：**
```
apps/api/tests/
├── unit_tests/         # 单元测试
│   ├── services/
│   ├── models/
│   └── utils/
├── integration_tests/  # 集成测试
├── fixtures/           # 测试固定数据
└── conftest.py        # pytest配置
```

**E2E测试结构：**
```
tests/e2e/
├── auth/               # 认证流程测试
├── chat/              # 聊天功能测试
├── profile/           # 用户资料测试
└── utils/             # E2E测试工具
```

---

**由BMAD™核心产品管理框架生成**