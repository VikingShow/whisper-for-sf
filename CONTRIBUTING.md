# 贡献指南

感谢你有兴趣为本项目做出贡献！🎉

## 如何贡献

### 报告 Bug

如果你发现了 bug，请创建一个 Issue，并包含以下信息：

- 详细的问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（操作系统、Python 版本、依赖版本等）
- 错误日志（如果有）

### 提出新功能

如果你有好的想法，欢迎创建 Feature Request：

- 描述新功能的目的和用途
- 说明为什么这个功能有用
- 提供可能的实现方案（可选）

### 提交代码

1. **Fork 项目**
   ```bash
   git clone https://github.com/yourusername/whisper.git
   cd whisper
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **编写代码**
   - 遵循现有代码风格
   - 添加必要的注释和文档字符串
   - 添加类型提示
   - 确保代码通过所有测试

5. **运行测试**
   ```bash
   pytest tests/ -v
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能的描述"
   ```

7. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建 Pull Request**
   - 描述你的更改
   - 链接相关的 Issue
   - 等待审核

## 代码规范

### Python 风格

- 遵循 PEP 8 规范
- 使用 4 个空格缩进
- 最大行长度 100 字符
- 函数和类使用文档字符串

### 提交信息

使用语义化的提交信息：

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 其他更改

示例：
```
feat: 添加 SRT 字幕格式支持
fix: 修复缓存路径生成错误
docs: 更新 README 使用说明
```

### 测试要求

- 新功能必须包含测试
- Bug 修复应该添加回归测试
- 确保测试覆盖率不降低
- 所有测试必须通过

### 文档要求

- 更新 README.md（如果需要）
- 添加函数文档字符串
- 更新 CHANGELOG.md

## 开发环境设置

### 推荐工具

- **IDE**: VS Code, PyCharm
- **Linter**: pylint, flake8
- **Formatter**: black, autopep8
- **Type Checker**: mypy

### VS Code 配置示例

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true
}
```

## 行为准则

- 尊重所有贡献者
- 保持友好和专业的沟通
- 接受建设性的反馈
- 专注于对项目最好的方案

## 需要帮助？

如果你在贡献过程中遇到问题：

- 查看已有的 Issues 和 Pull Requests
- 在 Issue 中提问
- 查阅项目文档

## 许可证

提交代码即表示你同意你的贡献将在 MIT 许可证下发布。

---

再次感谢你的贡献！ 🙏


