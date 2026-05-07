# 贡献指南

感谢你愿意改进 Rapid Inbox。这个项目偏向小而清晰的本地优先工具，贡献时请尽量保持实现直接、行为可测试、文档和代码同步。

## 开发环境

```bash
python3 -m venv .venv
.venv/bin/pip install -c constraints-dev.txt -e ".[dev]"
cp .env.example .env
.venv/bin/rapid-inbox-http
```

运行测试：

```bash
.venv/bin/pytest
```

## 提交前检查

请在提交 PR 前至少完成：

```bash
.venv/bin/pytest
python3 -m compileall -q app tests
```

如果改动只涉及文档，请确保链接、命令和文件名仍然准确。

## 分支与提交

- 从 `main` 拉出短分支，例如 `fix/api-key-validation` 或 `docs/readme-refresh`。
- 提交保持聚焦：一个提交最好只解决一个问题或一组紧密相关的改动。
- 提交信息可以使用中文，也可以使用 Conventional Commits 风格。
- 不要提交 `.env`、`storage/`、数据库文件、邮件样本中的真实密钥或个人数据。

## Pull Request

PR 描述建议包含：

- 改动目的
- 主要实现点
- 测试结果
- 兼容性或迁移影响
- 截图或录屏，若改动涉及页面

如果你准备做较大的功能、数据结构调整或行为变更，请先开 Issue 讨论方向，避免做完后发现目标不一致。

## 代码风格

- 优先沿用现有模块边界和函数风格。
- 业务逻辑要有测试覆盖，尤其是鉴权、权限、数据清理和恢复流程。
- 对外行为变更需要同步更新 README、相关文档或模板文案。
- 错误处理尽量明确，避免吞掉会影响数据一致性的异常。

## 报告问题

提交 Issue 时请尽量提供：

- 版本或提交哈希
- Python 版本
- 操作系统
- 启动方式
- 复现步骤
- 期望结果和实际结果
- 相关日志或截图

涉及密钥、邮件内容、真实域名、IP 地址或其他敏感信息时，请先脱敏。
