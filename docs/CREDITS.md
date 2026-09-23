# 参考与致谢

这份清单记录行旅项目的参与者、学习参考、依赖工具与数据服务，帮助读者了解各项能力的来源。

## 项目维护与协作角色

- **维护者：** [shjhijoaj](https://github.com/shjhijoaj) 负责旅行场景需求、功能取舍、Dify 配置、项目发布与后续维护。
- **AI 协作工具：** [OpenAI Codex](https://openai.com/codex/) 参与接口与前端实现、测试编写和执行、问题定位、文档整理与发布；以 AI 编程协作角色署名。

## 直接依赖与工具

| 项目 | 用途 | 入口 |
| --- | --- | --- |
| [FastAPI](https://fastapi.tiangolo.com/) | Python API、参数校验和交互式文档 | `api/` |
| [Uvicorn](https://www.uvicorn.org/) | ASGI 开发与容器服务 | `Dockerfile`、启动命令 |
| [HTTPX](https://www.python-httpx.org/) | 调用 Dify 和外部数据服务 | `api/` |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 从本地 `.env` 读取运行配置 | `api/`、`.env.example` |
| [pytest](https://pytest.org/) | API、规则和工作流校验 | `tests/` |
| [Playwright](https://playwright.dev/) | 浏览器回归测试 | `tests/browser-*.cjs` |
| [Docker](https://www.docker.com/) | 本地容器和 Compose 部署 | `Dockerfile`、`docker-compose*.yml` |
| [SQLite](https://www.sqlite.org/) | 单实例账号、偏好、历史和运行记录存储 | `api/history.py`、`api/accounts.py` |
| [GitHub Actions](https://github.com/features/actions) | 在推送和 Pull Request 时运行项目检查 | `.github/workflows/ci.yml` |

Python 依赖版本固定在 [`requirements.txt`](../requirements.txt)。具体授权请以各项目发布版本附带的许可证为准。

## 外部服务与数据来源

| 服务 | 在本项目中的作用 | 需要注意的边界 |
| --- | --- | --- |
| [Dify](https://github.com/langgenius/dify) | 编排知识检索、规划、检查和修正节点；模型凭证由用户在 Dify 中配置 | DSL 导入新环境后需重新选择模型和知识库；Key 只放在本机 `.env`，不提交到仓库 |
| [Open-Meteo](https://open-meteo.com/) | 城市确认后的天气预报快照 | 响应会保存来源和查询时间；天气不是实时保证，商业或规模化使用需核对供应商条款与额度 |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) / [Nominatim](https://operations.osmfoundation.org/policies/nominatim/) | 地点地理编码和地图搜索 | 遵守 Nominatim 使用政策和速率限制，规模化部署应使用合适的自有或商业服务 |
| [OSRM](https://project-osrm.org/) | 驾车道路距离与时间估算 | 结果不包含实时拥堵、公交或步行核验；公开演示服务存在使用限制 |

天气、地图和路线结果仅作为行程审阅信息。票价、开放时间、预约、库存和实际交通应由用户在出行前向官方渠道核实；本项目不会自动预订或声称保证结果准确。

## 内容与授权说明

- `knowledge/` 中的旅行知识是用于演示检索链路的示例内容，不代表对任何地点、价格、开放时间或官方信息的背书。
- `docs/images/` 中的界面截图使用固定的虚构行程，仅用于展示本项目界面。
- 仓库当前**未指定开源许可证**；第三方组件和服务分别遵循其上游许可证与条款。
- 请勿提交 API Key、Cookie、真实账号、个人行程、供应商私有资料或其他未获授权的第三方内容。发现归属或授权问题时，请通过 [Issue](https://github.com/shjhijoaj/smart-travel-agent/issues) 联系维护者。
