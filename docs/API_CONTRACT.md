# UniMatch API 契约

> 所有接口如无特别说明，返回统一 JSON：`{ "data": ..., "error": null, "message": null }`；错误时返回 `HTTPException` 或 `{ "error": "code", "message": "..." }`。
> 
> 认证：登录后获取 `access_token`，在请求头携带 `Authorization: Bearer <token>`。

---

## 1. 认证 (Auth)

### POST `/auth/send-verification-code`
发送邮箱/手机验证码。开发环境使用 mock 会在服务端日志打印验证码。
**学校邮箱白名单**：注册时邮箱后缀必须匹配 `ALLOWED_EMAIL_DOMAINS`（默认 `@shanghaitech.edu.cn`），否则返回 `400`。

**请求体：**
```json
{
  "email": "xxx@shanghaitech.edu.cn",
  "phone": null,
  "purpose": "register"  // register | login | reset_password
}
```

**响应：**
```json
{ "ok": true, "provider": "mock", "target": "xxx@shanghaitech.edu.cn" }
```

---

### POST `/auth/register`
邮箱验证码注册。手机号注册可选。

**请求体：**
```json
{
  "email": "xxx@shanghaitech.edu.cn",
  "phone": null,
  "code": "123456",
  "password": "string",
  "nickname": "小明",
  "school": "上海科技大学"
}
```

**响应：** 同 `/auth/login`，直接返回 token。

---

### POST `/auth/login`
邮箱/手机 + 密码登录。

**请求体：**
```json
{
  "email": "xxx@shanghaitech.edu.cn",
  "phone": null,
  "password": "string"
}
```

**响应：**
```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "uuid", "email": "...", "nickname": "...", "avatar_url": "..." }
}
```

---

### POST `/auth/refresh`
刷新 access token。

**请求体：**
```json
{ "refresh_token": "jwt" }
```

**响应：** 新的 access/refresh token。

---

### POST `/auth/logout`
前端调用后把当前 `Authorization: Bearer <token>` 加入黑名单（Redis），后端返回成功。请求需携带 token。

---

## 2. 当前用户 (Me)

### GET `/users/me`
返回当前用户基础信息 + 是否完成邮箱验证。

### PUT `/users/me`
更新基础信息：邮箱、手机号等（不可改昵称/头像，走 profile）。

### DELETE `/users/me`
注销账号，标记为删除，30 天后清理数据。

---

## 3. 个人资料 (Profile)

### GET `/profiles/me`
返回完整个人资料。

**响应字段：**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "nickname": "小明",
  "avatar_url": "https://...",
  "gender": "male",
  "birth_date": "2002-05-01",
  "age": 23,
  "education_level": "undergraduate",
  "school": "上海科技大学",
  "major": "计算机科学与技术",
  "mbti": "INTJ",
  "interests": ["篮球", "摄影", "Python"],
  "location": "上海浦东",
  "bio": "...",
  "research_direction": "计算机视觉",
  "dating_purpose": "恋爱",
  "family_status": "...",
  "ideal_person": "...",
  "is_verified_email": true,
  "is_verified_school": false,
  "created_at": "...",
  "updated_at": "..."
}
```

---

### PUT `/profiles/me`
更新个人资料。`nickname` 必填；其余字段按需。

**请求体：** 部分/全部字段。

---

### POST `/profiles/avatar`
上传头像。`multipart/form-data`，字段名 `file`。

**响应：**
```json
{ "avatar_url": "https://..." }
```

---

### POST `/profiles/consent`
用户同意某项授权（如读取出生日期/学历、聊天记录分析）。

**请求体：**
```json
{
  "consent_type": "chat_analysis",
  "granted": true
}
```

---

## 4. 发现 (Discovery)

### GET `/discovery/{section}`
section 取值：`academic` | `daily` | `dating`。

**查询参数：**
- `q`: 关键词搜索（昵称/学校/专业/兴趣）
- `push`: `true` 时返回系统推荐的 Top-10 优先，其余随机
- `page`, `limit`: 分页

**响应：**
```json
{
  "items": [
    {
      "user_id": "uuid",
      "nickname": "...",
      "avatar_url": "...",
      "age": 23,
      "education_level": "...",
      "major": "...",
      "interests": [...],
      "location": "...",
      "match_score": 0.85,
      "match_reason": "同专业、兴趣相近"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

---

### GET `/discovery/{section}/users/{user_id}`
查看某用户在该板块的详情页。

**响应：** 包含该板块的展示字段（`research_direction` 仅在 academic 显示，`dating_purpose` 仅在 dating 显示等）。

---

### POST `/discovery/{section}/push`
开启/关闭该板块的推送优先展示。

**请求体：**
```json
{ "enabled": true }
```

---

## 5. 问卷 (Questionnaire)

### GET `/questionnaires`
列出当前用户可用的问卷（按板块/全局）。

### GET `/questionnaires/{slug}`
获取问卷 JSON 定义（含题目、类型、选项）。

### POST `/questionnaires/{slug}/responses`
提交答卷。

**请求体：**
```json
{
  "answers": {
    "major": "计算机",
    "interests": ["篮球", "Python"],
    "mbti": "INTJ"
  }
}
```

### GET `/questionnaires/{slug}/responses/me`
获取当前用户的答卷。

---

## 6. 匹配推荐 (Match)

### GET `/matches/recommendations/{section}`
返回 Top-N 推荐用户（规则 + 向量相似度）。

**查询参数：** `limit`（默认 10）。

### POST `/matches/{user_id}/feedback`
对推荐用户反馈。

**请求体：**
```json
{ "section": "dating", "action": "like" }  // like | dislike | skip
```

---

## 7. 好友 (Friends)

### POST `/friends/requests`
发送好友申请。

**请求体：**
```json
{ "to_user_id": "uuid", "message": "你好，想一起学习" }
```

---

### GET `/friends/requests`
查询好友申请。`?direction=received|sent`。

**响应：**
```json
{
  "items": [...],
  "total": 5
}
```

### POST `/friends/requests/{request_id}/accept`
接受好友申请。

### POST `/friends/requests/{request_id}/reject`
拒绝好友申请。

### GET `/friends`
我的好友列表。

### DELETE `/friends/{user_id}`
删除好友。

---

## 8. 聊天 (Chat)

### WebSocket `/ws/chat?token=...`
- 连接后通过 JWT 认证。
- 事件：
  - `send_message`: `{ "conversation_id": "uuid", "content": "...", "message_type": "text" }`
  - `message_read`: `{ "message_id": "uuid" }`
  - `typing`: `{ "conversation_id": "uuid" }`
- 服务端推送：`new_message`, `message_read`, `typing`, `unread_update`。

### REST 备用接口

#### GET `/conversations`
当前用户的会话列表，按最后消息时间倒序。

**响应：**
```json
{
  "items": [
    {
      "id": "uuid",
      "participant": { "id": "uuid", "nickname": "...", "avatar_url": "..." },
      "last_message": { "content": "...", "created_at": "..." },
      "unread_count": 3
    }
  ]
}
```

#### GET `/conversations/{conversation_id}/messages`
历史消息，分页。

#### POST `/conversations/{conversation_id}/messages`
REST 方式发送消息（主要用于图片/无 WebSocket 场景）。

#### POST `/messages/{message_id}/read`
标记单条消息已读。

---

## 9. 留言板 (Message Board)

### GET `/message-board/{section}`
查询某板块的留言。可带 `?owner_id=uuid` 查看用户主页留言。

### POST `/message-board/{section}`
发表留言。

**请求体：**
```json
{ "owner_id": "uuid", "content": "..." }
```

---

## 10. 举报 (Reports)

### POST `/reports`
举报用户或消息。

**请求体：**
```json
{
  "target_type": "user",  // user | message | content
  "target_id": "uuid",
  "reason": "harassment",
  "description": "..."
}
```

---

## 11. AI (占位)

### POST `/ai/generate-questions`
根据当前画像生成进阶匹配问题。

**请求体：**
```json
{ "section": "daily", "count": 3 }
```

**响应：**
```json
{
  "questions": [
    { "id": "q1", "text": "你最喜欢的周末活动是？", "type": "single_choice", "options": [...] }
  ]
}
```

### POST `/ai/match-explanation`
生成匹配解释。

**请求体：**
```json
{ "target_user_id": "uuid", "section": "academic" }
```

---

## 12. 管理后台 (Admin)

- `GET /admin/users` 用户列表（分页、搜索）
- `PUT /admin/users/{user_id}/status` 启用/禁用
- `GET /admin/reports` 举报列表
- `PUT /admin/reports/{report_id}` 处理举报
- `GET /admin/moderation-logs` 审核日志

---

## 13. 状态码与错误

- `200 OK` 成功
- `201 Created` 创建成功
- `400 Bad Request` 参数错误、验证码错误、违禁词命中
- `401 Unauthorized` 未登录或 token 过期
- `403 Forbidden` 无权限
- `404 Not Found`
- `409 Conflict` 资源冲突（如已注册）
- `422 Validation Error` (FastAPI 自动)
- `429 Too Many Requests` 限流
