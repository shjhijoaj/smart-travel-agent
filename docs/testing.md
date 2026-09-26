# 行旅测试记录

2026-09-26 本地 Python 3.9：67 项 pytest 通过。原有协议/流式/账号/天气/路线/规则测试加上产品流程测试，覆盖手动计划、编辑与导出一致性、历史搜索分页与账号隔离、统计失败保护、无配置就绪状态、输入边界和生成限流。

真实浏览器完成：创建手动行程 → 编辑并保存 → 下载匹配 → 刷新后历史恢复 → 搜索 → 注册并接管游客历史 → 偏好保存 → 退出后隐藏私人内容；1440px 和 390px 布局无横向溢出，无 pageerror。

独立的真实 Dify 验收：上海至杭州、两天、两人，返回 source=dify、两天日程，无错误，57.37 秒。这是一次真实上游调用，不是吞吐或准确率基准。自动化测试默认禁用真实 Key，模型内容质量还需要人工确认。

## 重跑
`python -m pytest -q`、`python tests/validate_workflow_cases.py`、`python scripts/evaluate_cases.py`。

产品浏览器测试：独立实例设置 DIFY_API_KEY 为空、LOCAL_FALLBACK=true、WEATHER_ENABLED=false、TRAVEL_DB_PATH=test-results/ui/travel.db，以 8791 端口运行。安装 `npm install --no-save playwright@1.55.0` 和 `npx playwright install chromium`，执行 `node tests/browser-product.cjs`。测试会写模拟账号及行程，不要指向个人数据库；Windows 可设置 BROWSER_CHANNEL=msedge。

其他 browser-smoke / browser-account 用例包含固定上游响应，不能作为真实 AI 调用证据。运行记录成本为估算，不是供应商账单；尚未做生产压力和多实例验收。
