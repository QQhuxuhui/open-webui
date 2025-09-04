# 编码标准

## 关键全栈规则

- **类型共享：** 总是在packages/shared中定义类型并从那里导入
- **API调用：** 从不直接进行HTTP调用 - 使用服务层
- **环境变量：** 仅通过配置对象访问，从不直接使用process.env
- **错误处理：** 所有API路由必须使用标准错误处理程序
- **状态更新：** 从不直接变更状态 - 使用适当的状态管理模式

## 命名约定

| 元素 | 前端 | 后端 | 示例 |
|------|------|------|------|
| 组件 | PascalCase | - | `UserProfile.tsx` |
| Hooks | camelCase with 'use' | - | `useAuth.ts` |
| API路由 | - | kebab-case | `/api/user-profile` |
| 数据库表 | - | snake_case | `user_profiles` |

---

**由BMAD™核心产品管理框架生成**