"""Validated manual schedules and a single export representation for edited plans."""
from datetime import date, timedelta
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class Activity(BaseModel):
    time: str = Field(default="", max_length=40)
    place: str = Field(default="", max_length=160)
    fields: dict[str, str] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def bounded_fields(cls, values):
        if len(values) > 12 or any(len(k) > 60 or len(v) > 600 for k, v in values.items()):
            raise ValueError("每项活动最多 12 个字段，每个字段不超过 600 字")
        return values


class Day(BaseModel):
    title: str = Field(default="", max_length=160)
    date: Optional[str] = Field(default=None, max_length=10)
    activities: list[Activity] = Field(default_factory=list, max_length=20)

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        if value:
            date.fromisoformat(value)
        return value


class StructuredUpdate(BaseModel):
    days: list[Day] = Field(min_length=1, max_length=31)


def cell(value):
    return str(value or "").replace("|", "／").replace("\r", " ").replace("\n", " ")


def original_text(result):
    return result.get("answer") or result.get("plan") or "\n\n".join(str(v) for v in result.get("outputs", {}).values())


def edited_text(result, days):
    """Keep non-itinerary sections, replace daily content once, preserve original separately."""
    text = original_text(result)
    sections = re.split(r"(?m)(?=^## )", text)
    kept = [s for s in sections if not re.match(r"## .*?(每日|行程安排|daily|itinerary)", s, re.I)]
    # Older providers can omit a level-two daily heading. Drop its level-three days too.
    kept = [re.split(r"(?m)^### .*?(?:第[一二三四五六七八九十\d]+天|day\s*\d+)", s, maxsplit=1, flags=re.I)[0] for s in kept]
    kept = [s for s in kept if s.strip()]
    daily = ["## 每日行程（已编辑）"]
    for i, day in enumerate(days):
        theme = re.sub(r'^(?:第[一二三四五六七八九十\d]+天|day\s*\d+)\s*[·:：\s]*', '', cell(day.get('title')), flags=re.I)
        theme = re.sub(r'^\d{4}-\d{2}-\d{2}\s*[·:：\s]*', '', theme)
        daily += [f"### 第{i+1}天 · {cell(day.get('date'))} · {theme}", "| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |", "| --- | --- | --- | --- | --- |"]
        for activity in day.get("activities", []):
            fields = activity.get("fields") or {}
            note = "；".join(v for k, v in fields.items() if not re.search(r"时间|地点|活动|交通|费用|time|place", k, re.I))
            daily.append("| " + " | ".join(cell(v) for v in [activity.get("time"),activity.get("place"),fields.get("交通", "待确认"),fields.get("预计费用",fields.get("费用","待确认")),note]) + " |")
    introduction = kept.pop(0) if kept else ""
    return introduction.strip()+"\n\n"+"\n".join(daily)+"\n\n"+"\n\n".join(s.strip() for s in kept if s.strip())


def offline_plan(request):
    start, end = (date.fromisoformat(x) for x in request.travel_dates.split("/"))
    lines = ["## 行程概览", f"{cell(request.departure)} → {cell(request.destination)} · {request.companions} 人 · {request.travel_dates}", "这是本地手动规划模板，不是 AI 生成结果。请把每日活动替换成你确认过的地点和时间。", "## 每日行程"]
    for i in range((end-start).days+1):
        lines += [f"### 第{i+1}天 · {start+timedelta(days=i)} · 自由安排", "| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |", "| --- | --- | --- | --- | --- |", "| 09:00—11:00 | 待确认：上午活动 | 待确认 | 待确认 | 在可编辑行程中填写具体地点 |", "| 12:00—13:00 | 待确认：午餐与休息 | 待确认 | 待确认 | 预留休息时间 |", "| 14:00—17:00 | 待确认：下午活动 | 待确认 | 待确认 | 核实开放时间与预约 |"]
    lines += ["## 预算估算",f"所有同行人预算上限：{request.budget} 元。这是你的预算，不是已经核实的报价。", "| 项目 | 所有人合计费用 |", "| --- | --- |", "| 往返交通 | 待确认 |", "| 住宿 | 待确认 |", "| 餐饮与活动 | 待确认 |", "## 下雨备选方案", "选择已确认开放的室内场所；本地模式不提供实时天气。", "## 注意事项", "- 出发前确认交通、住宿、证件和预约。", "- 编辑后保存，再下载或打印；原始文本单独保留。"]
    return {"success":True,"source":"local-fallback","plan":"\n".join(lines),"warnings":["本地手动规划模式：未调用大语言模型，地点、价格与天气需要自行确认。"]}
