"""Deterministic travel checks that decide when a local partial replan is needed."""
import re


def review(request, weather=None, route=None, plan=""):
    actions = []
    rain_days = [day["date"] for day in (weather or {}).get("days", []) if (day.get("rain_percent") or 0) >= 60]
    if rain_days:
        actions.append({"type": "weather", "priority": "high", "message": f"{', '.join(rain_days)} 降雨概率较高，建议将户外活动替换为室内备选。"})
    duration = (route or {}).get("duration_min")
    if isinstance(duration, (int, float)) and duration > 180:
        actions.append({"type": "route", "priority": "high", "message": f"地点串联道路估算约 {duration} 分钟，建议拆分为相邻片区。"})
    closed = re.findall(r"([^，。；\n]{1,30})(?:闭馆|关闭|暂停开放|不可用)", plan)
    if closed:
        actions.append({"type": "closure", "priority": "high", "message": f"发现可能无法使用的地点：{'、'.join(closed[:3])}，需要替换并重新确认开放状态。"})
    if not actions:
        actions.append({"type": "ok", "priority": "low", "message": "当前天气和路线检查未触发局部调整。"})
    return {"status": "needs_replan" if any(a["priority"] == "high" for a in actions) else "ok", "actions": actions,
            "next_step": "按高优先级问题调整受影响日期，再重新生成该版本。" if actions[0]["type"] != "ok" else "可直接执行，出发前再次确认实时信息。"}
