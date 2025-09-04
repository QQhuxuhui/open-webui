# API规范

## REST API规范

```yaml
openapi: 3.0.0
info:
  title: Open WebUI 合规API
  version: 1.0.0
  description: 增强的Open WebUI API，具有包括手机验证、内容标识和用户管理在内的合规功能
servers:
  - url: https://api.openwebui.com/v1
    description: 生产服务器
  - url: http://localhost:5000/api/v1
    description: 开发服务器

security:
  - BearerAuth: []
  - SessionAuth: []

paths:
  # 认证和用户管理
  /auth/phone/register:
    post:
      summary: 用手机号注册用户
      tags: [认证]
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [phone_number, verification_code, privacy_consent, terms_consent]
              properties:
                phone_number:
                  type: string
                  pattern: '^(\+|00)[1-9]\d{1,14}$'
                verification_code:
                  type: string
                  minLength: 4
                  maxLength: 8
                nickname:
                  type: string
                  maxLength: 50
                privacy_consent:
                  type: boolean
                  enum: [true]
                terms_consent:
                  type: boolean
                  enum: [true]
      responses:
        201:
          description: 用户注册成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  user:
                    $ref: '#/components/schemas/User'
                  token:
                    type: string

  /auth/phone/login:
    post:
      summary: 用手机号和验证码登录
      tags: [认证]
      security: []
      responses:
        200:
          description: 登录成功

  /auth/phone/send-code:
    post:
      summary: 发送短信验证码
      tags: [认证]
      security: []
      responses:
        200:
          description: 短信验证码发送成功

  /users/profile:
    get:
      summary: 获取当前用户资料
      tags: [用户管理]
      responses:
        200:
          description: 用户资料获取成功
    put:
      summary: 更新用户资料
      tags: [用户管理]
      responses:
        200:
          description: 资料更新成功

  /users/verification/real-name:
    post:
      summary: 提交实名验证
      tags: [验证]
      responses:
        201:
          description: 验证提交成功
    get:
      summary: 获取实名验证状态
      tags: [验证]
      responses:
        200:
          description: 验证状态获取成功

  /content/reports:
    post:
      summary: 提交内容举报
      tags: [内容审核]
      responses:
        201:
          description: 举报提交成功
    get:
      summary: 获取用户提交的举报
      tags: [内容审核]
      responses:
        200:
          description: 举报获取成功

components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        phone_number:
          type: string
        phone_verified:
          type: boolean
        real_name:
          type: string
        real_name_verified:
          type: boolean
        nickname:
          type: string
        avatar_url:
          type: string
          format: uri
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    SessionAuth:
      type: apiKey
      in: cookie
      name: session_id
```

---

**由BMAD™核心产品管理框架生成**