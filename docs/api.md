# API

本地交互文档：`http://127.0.0.1:8010/docs`。Docker 对应 8000 端口。

本版提供结构化日程编辑、路线估算、局部调整和运行遥测；固定案例评测执行 `python scripts/evaluate_cases.py`，不调用真实模型。

## 账号与记忆

| 方法与路径 | 请求/行为 |
| --- | --- |
| POST /api/account/register | username、password；注册并登录 |
| POST /api/account/login | 同上；登录 |
| GET /api/account/me | 返回 user，游客为 null |
| POST /api/account/logout | 撤销当前会话 |
| PUT /api/account/password | old_password、new_password；撤销其他会话并更新当前会话 |
| GET /api/account/memory | 读取 content、updated，需登录 |
| PUT /api/account/memory | content，最多 1,500 字符 |
| DELETE /api/account/memory | 删除偏好，保留历史 |

用户名 3–40 位英文、数字、下划线，不区分大小写；密码 10–128 字符。HttpOnly / SameSite=Strict 会话 Cookie 有效期 7 天，HTTPS 下启用 Secure。密码使用随机盐及 600,000 次 PBKDF2-HMAC-SHA256，数据库只存会话摘要。登录连续失败 5 次后，该用户名与客户端地址组合限流 5 分钟。

命令行需保存并复用 Cookie。账号登录可接收当前游客浏览器的历史。跨站写请求被拒绝；API 响应不缓存。

## 旅行请求

共同字段：departure、destination、travel_dates、budget、companions、preferences、language（默认中文）。日期格式 YYYY-MM-DD/YYYY-MM-DD，最多 31 天；预算为所有人的总预算正数，人数为正整数。

可选 `weather_location_id` 为城市候选的正整数 ID；`use_memory` 默认为 true。两字段由 API 消费，不作为额外输入发送 Dify。

| 方法与路径 | 行为 |
| --- | --- |
| GET /api/health | 进程存活检查，不代表外部模型可用 |
| POST /api/travel/weather | Open-Meteo 天气快照，歧义时返回 candidates |
| POST /api/travel/route | 地点地理编码和 OSRM 道路距离/时间估算；请求 destination 与 2–12 个 stops |
| POST /api/travel/review | 根据天气、路线和方案触发雨天、路线过长、闭馆检查 |
| POST /api/travel/local-adjust | 将高优先级调整原因写入结构化日程，供用户确认 |
| GET /api/telemetry/summary | 当前账号的运行次数、成功率、耗时、估算令牌和成本 |
| POST /api/travel/plan | 阻塞生成 |
| POST /api/travel/stream | SSE 生成 |
| GET /api/history | 当前账号或游客最近 100 条 |
| GET /api/history/{id} | 当前用户的方案详情 |
| DELETE /api/history/{id} | 删除单条历史 |
| POST /api/history/{id}/replan | 阻塞生成新版本，保留原记录 |
| POST /api/history/{id}/stream | SSE 生成新版本 |
| PATCH /api/history/{id}/structured | 保存用户编辑后的 validation.days，不覆盖模型原文 |

成功生成包含 plan_id、created_at、validation、weather；Chatflow 返回 answer，Workflow 返回 outputs。sources 是 Dify 提供的检索元数据，可能为空。validation 的金额未知时 calculated_total 为 null。保存失败附 save_warning，仍可下载方案。

## SSE 协议

使用 POST 和 fetch ReadableStream，请求体同旅行请求。响应 Content-Type 为 text/event-stream，每个事件由空行分隔，data 为 JSON：

```text
event: delta
data: {"event":"delta","text":"正文片段"}

event: complete
data: {"event":"complete","result":{"plan_id":"...","answer":"完整正文"}}
```

事件类型：status（节点状态）、weather、delta、replace（替换累计正文）、complete、error。只在 complete 后将结果视为成功；开始流后上游错误通过 error 表达，此时 HTTP 仍为 200。正常输入校验错误在流开始前返回 422。断开连接时尽力调用 Dify stop，不保存未完成方案；不提供断点续传。

阻塞模式超时返回 504，上游失败返回 502；输入校验失败返回 422。无 Key 且 LOCAL_FALLBACK=true 时输出明确标注的演示。历史与偏好存于 TRAVEL_DB_PATH（默认 data/travel.db）。
