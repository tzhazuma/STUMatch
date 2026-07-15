# UniMatch 贡献指南

感谢你对 UniMatch 校园同学匹配平台的关注！本指南帮助新贡献者快速了解如何参与项目。

---

## 开发流程

1. **Fork 仓库**（外部贡献者）或基于 `main` 分支创建新分支。
2. 在分支上进行开发，并遵循下方的代码风格规范。
3. 提交前确保相关测试通过、前端构建成功。
4. 提交 Pull Request，简要描述改动目的与验证方式。
5. 至少一位维护者 Code Review 通过后合并。

---

## 分支命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能 | `feature/<简短描述>` | `feature/user-report` |
| 修复 | `fix/<简短描述>` | `fix/websocket-reconnect` |
| 文档 | `docs/<简短描述>` | `docs/api-contract-update` |
| 基础设施 | `infra/<简短描述>` | `infra/docker-build-cache` |
| 重构 | `refactor/<简短描述>` | `refactor/match-score-calc` |

---

## 提交信息规范

建议采用 `<type>: <short description>` 格式，可选项包括：

- `feat`：新功能
- `fix`：Bug 修复
- `docs`：文档更新
- `style`：代码格式调整（不影响功能）
- `refactor`：重构
- `test`：测试相关
- `chore`：构建/工具/依赖更新

示例：

```bash
git commit -m "feat: add friend request notification"
git commit -m "fix: handle missing avatar_url in profile response"
git commit -m "docs: update AI provider configuration examples"
```

---

## 代码风格

### Python（后端）

- 使用 [Black](https://github.com/psf/black) 或 [Ruff](https://github.com/astral-sh/ruff) 格式化代码。
- 导入顺序：`stdlib` → `third-party` → `first-party`。
- 使用类型注解，关键函数必须包含 docstring。
- 变量与函数名使用 `snake_case`，类名使用 `PascalCase`。
- 常量定义在模块顶部，使用 `UPPER_CASE`。

示例：

```python
from datetime import datetime
from fastapi import FastAPI
from unimatch.models.user import User

app = FastAPI()

MAX_RETRY_COUNT = 3


def get_user_by_email(email: str) -> User | None:
    """根据邮箱查询用户，不存在时返回 None。"""
    ...
```

### TypeScript / React（Web & Mobile）

- 使用项目已配置的 TypeScript 严格模式。
- 组件与函数使用语义化命名，避免单字母变量。
- 使用 `async/await` 处理异步逻辑。
- 状态管理优先使用 Zustand，避免深层 prop drilling。
- 样式优先使用 Tailwind CSS（Web）。

---

## 测试要求

- 新增后端接口或复杂逻辑时，请补充对应单元测试。
- 运行后端测试：

  ```bash
  cd services/backend
  pytest
  ```

- 运行 Web 构建：

  ```bash
  cd apps/web
  npm run build
  ```

---

## 环境变量与密钥

- 永远不要将真实 API Key、数据库密码、JWT 密钥等提交到 Git 仓库。
- 新增环境变量时，同步更新 `.env.example` 与相关文档。
- 敏感配置在 CI 中通过 GitHub Secrets 注入。

---

## 安全与合规

- 涉及用户个人信息（邮箱、手机号、聊天记录、画像等）的功能需符合《个人信息保护法》及学校相关规定。
- 不收集身份证号等超出必要范围的个人信息。
- 引入第三方依赖前，请检查其许可证与安全性。

---

## 沟通与协作

- 遇到问题或对功能有疑问，请先查看 `README.md` 与 `docs/API_CONTRACT.md`。
- 提交 PR 前请自行 review 一次，确保没有遗漏的调试代码或敏感信息。
- 欢迎通过 Issue 或 Pull Request 参与讨论。

---

## 致谢

每一次贡献都让 UniMatch 变得更好，感谢你的参与！
