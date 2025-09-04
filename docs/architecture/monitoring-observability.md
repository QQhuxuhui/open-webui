# 监控和可观测性

## 监控栈

- **前端监控：** Sentry用于错误跟踪，Web Vitals用于性能监控
- **后端监控：** AWS CloudWatch用于基础设施监控，Sentry用于应用错误
- **错误跟踪：** Sentry集成前后端错误收集
- **性能监控：** New Relic用于APM，CloudWatch用于基础设施指标

## 关键指标

**前端指标：**
- Core Web Vitals (LCP, FID, CLS)
- JavaScript错误率
- API响应时间
- 用户交互跟踪

**后端指标：**
- 请求速率和响应时间
- 错误率按端点分类
- 数据库查询性能
- 资源利用率 (CPU, 内存)

---

**由BMAD™核心产品管理框架生成**