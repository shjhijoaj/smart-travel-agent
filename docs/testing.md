# 测试与真实联调

2026-09-22：59 个 pytest、2 个工作流规则场景和 2 个固定评测场景通过。pytest 使用临时 SQLite 和模拟上游，不读取或修改用户历史；固定评测写入 test-results/evaluation.db。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/validate_workflow_cases.py
```

覆盖输入边界、模型异常、推理过滤、历史版本、账号隔离、到期/撤销、错误登录限流、改密、长期记忆开关、SSE 完成与中断、跨片段标签过滤、城市歧义与手动选择、预报覆盖和预算检查。

## 浏览器回归

先启动 8010 服务，再执行：

```text
npm install --no-save playwright@1.55.0
npx playwright install chromium
node tests/browser-smoke.cjs
node tests/browser-account.cjs
```

可设置 `TRAVEL_URL` 指向 Docker 的 8000 端口，或用 `BROWSER_PATH` 指向本机浏览器。常规 UI 测试模拟模型/天气，账号测试使用真实账号 API，会创建随机测试账号。

## 真实验收（会调用模型）

```powershell
.\.venv\Scripts\python.exe scripts/accept_live.py
$env:TRAVEL_URL='http://127.0.0.1:8000'
.\.venv\Scripts\python.exe scripts/accept_live.py
node tests/live-browser.cjs
```

`accept_live.py` 检查真实天气、登录后偏好读取、Dify 增量、完成、历史保存，并清理自己的方案/偏好；随机测试账号保留。验收结果写入 `test-results/acceptance-v1.json` 和 `live-v1-result.json`，重复执行会更新记录。不要公开含账号或个人行程的原始测试记录。

本次 Docker 实测：天气 ok；1,066 个增量片段；最终正文 1,659 字符；首段约 45 秒；5 条检索来源。真实测试结果不能证明所有生成建议都准确。

## 容器持久化

```powershell
.\.venv\Scripts\python.exe scripts/check_docker_persistence.py
```

该脚本连接 8000，创建自己的账号/记忆，然后重启本项目旅行 API 容器，重新登录并读取记忆。会短暂中断正在进行的生成，请在空闲时运行。本次已通过；不会重启 Dify。

CI 执行常规 API/浏览器测试和 Docker 构建，不使用真实 Key 或真实模型额度。GitHub 上首次运行结果需要推送后确认。
