from api.itinerary import analyze, money


def test_conflicts_and_independent_arithmetic():
    text = '''## 每日行程
### 第1天 · 2026-10-03
| 时间 | 地点 |
|---|---|
| 09:00-11:00 | 西湖 |
| 10:30-12:00 | 西湖 |
## 预算估算
| 项目 | 所有人总费用 |
|---|---|
| 住宿 | 1200 |
| 餐饮 | 600 |
| 合计 | 1000 |
'''
    result = analyze(text, '2026-10-03/2026-10-03', '1500')
    assert result['calculated_total'] == '1800'
    assert {i['code'] for i in result['issues']} == {'time_overlap','duplicate_place','budget_exceeded','budget_arithmetic'}


def test_uncertain_money_is_not_guessed():
    for value in ['300-500', '约500', '待确认', '500/人', 'NaN']:
        assert money(value) is None
    assert str(money('¥1,200.50元')) == '1200.50'


def test_unparsed_plan_is_not_passed_as_valid():
    result = analyze('一段没有结构的文章', '2026-10-03/2026-10-05', '5000')
    assert result['status'] == 'needs_review'
    assert result['calculated_total'] is None


def test_adjacent_times_do_not_overlap():
    result = analyze('### 第1天 · 2026-10-03\n| 时间 | 地点 |\n|---|---|\n| 09:00-10:00 | A |\n| 10:00-11:00 | B |',
                     '2026-10-03/2026-10-03', '1000')
    assert result['issues'] == []
