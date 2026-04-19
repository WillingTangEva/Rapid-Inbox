# Public Mailbox WebSocket Design

## Goal

让公开收件箱第一页在收到新邮件后自动更新，无需手动刷新页面。

## Scope

### In Scope

- 复用现有 `runtime.live_state` 实时事件总线
- 为公开收件箱第一页提供 WebSocket 路由
- 新邮件到达后自动插入列表顶部
- 邮件解析完成后自动更新同一条卡片
- 复用现有列表卡片字段与验证码识别逻辑
- 为 WebSocket 路由和页面脚本增加自动化测试

### Out Of Scope

- 非第一页分页的实时重排
- 详情页实时更新
- 新建独立消息队列或外部 pub/sub

## Current Context

- 公开收件箱页面由 `app/http/public_views.py` 和 `app/templates/public/mailbox.html` 提供
- SMTP 实时事件存储在 `runtime.live_state`
- 管理台已经通过 `app/http/sse.py` 读取 `live_state` 做 SMTP 活动流展示
- 当前公开收件箱页是静态首屏渲染，收到新邮件后需要手动刷新

## Design

### Event Reuse Strategy

不新增新的实时总线，继续使用 `runtime.live_state`。

为了让公开收件箱能准确定位某个 `delivery_id` 属于哪个邮箱，现有 SMTP 事件会在同一条总线上补充两类邮箱投递事件：

- `mailbox_delivery`
- `mailbox_delivery_updated`

这两类事件都带：

- `mailbox`
- `delivery_id`
- `message_id`
- `rcpt_to`
- `parse_status`
- `ts`

`mailbox_delivery` 用于列表插入 pending 卡片，`mailbox_delivery_updated` 用于解析完成后更新同一条卡片。

### Backend Flow

#### Message Accept

在 `RapidInboxRuntime.accept_message()` 成功写入 `message_deliveries` 后，为每个收件人发布一条 `mailbox_delivery` 事件。

#### Parse Complete

在异步解析流程完成后，按该消息对应的每个 `delivery_id` 发布 `mailbox_delivery_updated` 事件。

#### WebSocket Route

在 `app/http/public_views.py` 增加：

- `/mail/{mailbox_address}/ws`

连接建立后：

1. 校验邮箱仍然允许公开访问
2. 从页面首屏注入的 `after_cursor` 开始消费 `live_state`
3. 只保留当前邮箱对应的 `mailbox_delivery` / `mailbox_delivery_updated` 事件
4. 调用消息服务获取该 `delivery_id` 对应的列表卡片 payload
5. 以 JSON 形式推送给前端

### Data Assembly

`MessageService` 增加“按 `delivery_id` 获取单条公开收件箱列表项”的 helper。

该 helper 复用现有列表项准备逻辑，包括：

- 主题
- 发件人
- 时间
- 附件状态
- 解析状态
- 验证码识别

这样首屏列表和 WebSocket 增量卡片保持完全一致的数据语义。

### Frontend Behavior

只在 `offset=0` 的第一页连接 WebSocket。

收到 `mailbox_delivery` 后：

- 以 `delivery_id` 去重
- 插入列表顶部
- 如果当前页已满 `limit` 条，删除最后一条
- 更新邮件总数和显示区间
- 如果原来是空状态，则替换为空列表

收到 `mailbox_delivery_updated` 后：

- 按 `delivery_id` 找到已有卡片
- 只更新该卡片的可见字段，不重复插入

### Error Handling

- WebSocket 断开后前端自动重连
- 连接失败时页面保持可用，只是退化为手动刷新
- 如果服务端收到事件但对应投递尚不可查询，则跳过该次推送

## Testing

需要覆盖：

1. WebSocket 连接后，目标邮箱收到新邮件时会收到对应卡片 payload
2. 其他邮箱的新邮件不会串流到当前邮箱连接
3. 模板第一页包含 WebSocket 初始化脚本与游标
4. 新邮件 payload 复用现有验证码识别结果

## Risks And Mitigations

- 风险：`live_state` 事件字段不足以映射邮箱与 delivery
  - 缓解：继续复用 `live_state`，但补发面向邮箱的投递事件
- 风险：前端与首屏模板渲染结构不一致
  - 缓解：服务端继续输出统一的列表项字段，前端只负责渲染和更新
- 风险：分页页码被实时插入打乱
  - 缓解：只对第一页启用实时插入
