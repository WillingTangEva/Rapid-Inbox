# 更新日志

本项目遵循语义化版本的思路记录重要变化。当前还处于 `0.x` 阶段，接口和数据结构可能继续调整。

## Unreleased

- 让 SMTP 监听器按 `MAX_MESSAGE_SIZE_BYTES` 传入 `data_size_limit`，避免被 aiosmtpd 默认 32 MB 限制截断。
- 管理员登录失败时也写入审计日志，方便事后追踪爆破尝试。
- 清理 SMTP per-IP 限流窗口中的过期条目，防止长期运行后内存缓慢增长。
- 修正 `_apply_parsed_message` 中 INSERT attachment 的缩进风格。
- 更正 README：邮件默认保留时间从 20 分钟修正为 10 分钟，与代码和测试一致。
- 完善 API 密钥编辑、授权范围和状态管理。
- 增加邮件自动保留与过期清理能力。
- 增强清空邮件数据后的文件清理和 SQLite 压缩流程。
- 整理 README、贡献指南、安全策略和 GitHub 协作模板。

## 0.1.0

- 提供 SMTP 收件、公开收件箱、管理后台和 HTTP API 的基础能力。
- 支持本地 SQLite 与磁盘文件持久化。
- 支持域名、邮箱、消息、附件、API Key、审计和系统设置管理。
- 支持启动恢复、邮件解析、HTML 预览和实时收件更新。
