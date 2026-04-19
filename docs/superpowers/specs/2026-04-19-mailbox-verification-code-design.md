# Mailbox Verification Code Shortcut Design

## Goal

在公开收件箱列表页 `/mail/{mailbox}` 中，为高置信度验证码邮件增加“直接复制验证码”能力，让用户不进入详情页也能快速拿到验证码。

## Scope

### In Scope

- 只在公开收件箱列表页显示验证码快捷入口
- 只提取 `4-8` 位纯数字验证码
- 只在上下文明确命中时显示验证码
- 对 OpenAI 验证邮件做额外优化
- 为复制按钮提供前端反馈
- 为识别规则和页面渲染补充自动化测试

### Out Of Scope

- 单封邮件详情页的验证码展示
- 非数字验证码
- 跨邮件关联、时间锚点、验证码消费状态
- 后台管理页或公开 API 的验证码输出

## Current Context

- 收件箱列表页模板位于 `app/templates/public/mailbox.html`
- 列表页数据由 `app/http/public_views.py` 调用 `app/services/messages.py` 获取
- 底层列表查询位于 `app/runtime.py:get_mailbox_view`
- 当前列表项只包含主题、发件人、附件状态和解析状态，不包含正文路径或验证码字段

## Design

### Data Flow

`RapidInboxRuntime.get_mailbox_view()` 扩展列表查询，额外返回：

- `text_preview`
- `text_body_path`
- `html_body_path`

`MessageService.get_public_mailbox_view()` 在运行时列表结果上补充验证码识别结果：

1. 先用 `from_addr`、`subject`、`text_preview`、`parse_status` 做预筛
2. 仅对疑似验证码邮件读取 `text_body` / `html_body`
3. 将识别结果写回列表项字段 `verification_code`

模板只消费 `verification_code`，不承担识别逻辑。

### Recognition Rules

基础规则：

- 只接受 `4-8` 位纯数字
- 需要命中明显上下文关键词，例如：
  - `验证码`
  - `校验码`
  - `verification code`
  - `verify code`
  - `one-time code`
  - `one time code`
  - `otp`
- 如果正文中存在多个不同候选值，则放弃识别
- 如果只有数字、没有上下文，也放弃识别

OpenAI 优化：

- 发件人优先信任：
  - `noreply@openai.com`
  - `no-reply@openai.com`
  - `@openai.com`
  - `.openai.com`
- 主题或正文额外识别：
  - `your openai verification code`
  - `your openai code`
  - `verify your email`
- 对 OpenAI 候选邮件，允许使用“OpenAI 发件人/文本命中 + 单一 4-8 位数字 + 验证关键词命中”的规则判定

### HTML Handling

HTML 正文不会直接按原始标签文本匹配，而是：

1. 去除标签
2. 解码实体
3. 合并连续空白

这样尽量避免样式数字、追踪参数、图片尺寸误判。

### UI Behavior

列表项识别出验证码后，在同一条邮件卡片中展示：

- 验证码徽标，例如 `验证码 123456`
- 复制按钮，例如 `复制`

点击后使用 `navigator.clipboard.writeText()` 复制验证码，并短暂反馈成功状态，例如按钮文本切换为 `已复制`。

未识别出验证码的邮件保持现状，不增加空占位。

## Error Handling

- `parse_status != parsed` 的邮件不尝试深读正文
- 缺失正文文件时静默跳过，不阻断列表页渲染
- 剪贴板 API 失败时不抛出页面错误，只恢复按钮状态

## Testing

需要覆盖：

1. 正常验证码邮件可在列表页显示复制入口
2. OpenAI 验证码邮件可被稳定识别
3. 没有关键词但带数字的邮件不会误判
4. 存在多个不同候选验证码时不会显示复制入口
5. HTML 邮件中的验证码可被识别

## Risks And Mitigations

- 风险：列表页读取正文带来额外 IO
  - 缓解：先预筛，再按需读取正文
- 风险：HTML 中杂讯数字误判
  - 缓解：只接受上下文明确命中的单一候选
- 风险：模板逻辑变复杂
  - 缓解：模板只渲染 `verification_code` 字段，识别逻辑集中在服务层
