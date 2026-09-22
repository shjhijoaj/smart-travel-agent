"""Conservative Markdown extraction and deterministic checks; no invented fields."""
import re
from datetime import date
from decimal import Decimal


def money(value):
    """Only unambiguous all-party numeric amounts qualify for arithmetic."""
    match = re.fullmatch(r'\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:元)?\s*', value.replace('**', ''))
    return Decimal(match[1].replace(',', '')) if match else None


def analyze(text, travel_dates, budget):
    days, costs, issues = [], [], []
    current = None
    headers = None
    budget_section = False
    for line in text.splitlines():
        clean = line.strip().replace('**', '')
        heading = re.match(r'^#{1,6}\s+(.+)', clean)
        if heading:
            title = heading[1]
            headers = None
            if re.search(r'预算|budget', title, re.I):
                budget_section = True
                current = None
            elif re.search(r'第[一二三四五六七八九十\d]+天|day\s*\d+', title, re.I):
                budget_section = False
                found = re.search(r'\d{4}-\d{2}-\d{2}', title)
                current = dict(title=title, date=found[0] if found else None, activities=[])
                days.append(current)
            else:
                budget_section = False
                current = None
            continue
        if not clean.startswith('|'):
            headers = None
            continue
        cells = [x.strip() for x in clean.strip('|').split('|')]
        if all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
            continue
        if headers is None:
            headers = cells
            continue
        if budget_section and len(cells) >= 2:
            # Per-person, per-day and unspecified multi-column tables are not totals.
            unit_safe = len(headers) == 2 and not re.search(r'每人|人均|per person|每天|per day', ' '.join(headers), re.I)
            amount = money(cells[1]) if unit_safe else None
            costs.append(dict(label=cells[0], raw=cells[1], amount=str(amount) if amount is not None else None,
                              is_total=bool(re.fullmatch(r'合计|总计|总费用|total', cells[0], re.I))))
        elif current is not None:
            row = dict(zip(headers, cells))
            time = next((v for k, v in row.items() if re.search(r'时间|时段|time', k, re.I)), '')
            place = next((v for k, v in row.items() if re.search(r'地点|景点|location|place', k, re.I)), '')
            current['activities'].append(dict(time=time, place=place, fields=row))
    start, end = (date.fromisoformat(x) for x in travel_dates.split('/'))
    expected = (end-start).days+1
    if len(days) != expected:
        issues.append(dict(code='day_count', message=f'请求 {expected} 天，识别到 {len(days)} 个每日分区，请确认是否遗漏。'))
    for day in days:
        spans, places = [], set()
        if day['date']:
            try:
                parsed = date.fromisoformat(day['date'])
                if not start <= parsed <= end:
                    issues.append(dict(code='date_outside', message=f"{day['title']} 不在请求日期内。"))
            except ValueError:
                issues.append(dict(code='invalid_date', message=f"{day['title']} 的日期不存在。"))
        for activity in day['activities']:
            match = re.fullmatch(r'(\d{1,2}):(\d{2})\s*[-—–~～至]\s*(\d{1,2}):(\d{2})', activity['time'])
            if match:
                h1, m1, h2, m2 = map(int, match.groups())
                a, b = h1*60+m1, h2*60+m2
                if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59 or b <= a:
                    issues.append(dict(code='invalid_time', message=f"{day['title']}：时间段 {activity['time']} 无效或跨天，需确认。"))
                else:
                    if any(a < y and b > x for x, y in spans):
                        issues.append(dict(code='time_overlap', message=f"{day['title']}：{activity['time']} 与其他活动重叠。"))
                    spans.append((a,b))
            if activity['place'] and activity['place'] in places:
                issues.append(dict(code='duplicate_place', message=f"{day['title']}：重复安排 {activity['place']}，请确认。"))
            places.add(activity['place'])
    items = [x for x in costs if not x['is_total']]
    totals = [x for x in costs if x['is_total']]
    calculated = sum((Decimal(x['amount']) for x in items), Decimal(0)) if items and all(x['amount'] is not None for x in items) else None
    if calculated is not None:
        if calculated > Decimal(budget):
            issues.append(dict(code='budget_exceeded', message=f'预算明细相加为 {calculated} 元，超过预算 {budget} 元。'))
        if len(totals) == 1 and totals[0]['amount'] is not None and Decimal(totals[0]['amount']) != calculated:
            issues.append(dict(code='budget_arithmetic', message=f"预算明细合计 {calculated} 元，与模型填写的 {totals[0]['amount']} 元不一致。"))
    return dict(days=days, budget_items=costs, calculated_total=str(calculated) if calculated is not None else None,
                issues=issues, status='needs_review' if issues else 'no_detected_conflict',
                limits='仅检查可识别的日期、时间与明确金额；未验证真实路线耗时、票价、开放时间。未发现冲突不等于行程已核实。')
