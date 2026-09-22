# 复现 Dify 应用

1. 导入 workflow/smart-travel-agent.yml，类型为 advanced-chat（Chatflow）。
2. 安装声明的模型插件，在工作区填写自己的凭证，并为两个 LLM 节点选择可用模型。
3. 建立知识库，上传 knowledge/travel-knowledge.md；样例以广州为主。
4. 在“旅行知识检索”节点重新选择知识库，原 dataset_ids 不能跨工作区复用。
5. 确认“行程规划”节点启用 context，指向“旅行知识检索 / result”；知识参考提示词使用 `{{#context#}}`。
6. 测试正常预算与低预算分支，确认最终答案，然后发布。
7. 创建应用 API Key，仅填本机 .env，DIFY_APP_MODE=advanced-chat。

当前本机应用已于 2026-09-22 完成第 5 步并重新发布。仓库 DSL 来自此已发布版本的无密钥导出，真实调用返回知识检索元数据。

宿主机运行时 DIFY_BASE_URL=http://localhost。本机 Dify Docker 用户优先按 README 使用 docker-compose.dify.yml，通过已有 docker_default 网络访问 http://nginx；网络名可用 DIFY_DOCKER_NETWORK 调整。远程 Dify 设置 DIFY_DOCKER_BASE_URL。

## 已有本机应用的修复脚本

scripts/dify_reference_update.py 适配本次 Dify 1.17.1 及固定节点 ID，仅供维护该应用；新应用优先使用界面检查。脚本必须在 Dify API 容器内执行，默认只读，--apply 会备份图并发布新版本，--export 导出当前已发布 DSL（不含密钥）。不要对无关应用直接套用节点 ID。

API 层向 preferences 追加简洁格式、天气、可选偏好及旧方案上下文；上游仍输出 Markdown。后端提取和规则检查只处理可识别字段，不等同于实时路线核验。
