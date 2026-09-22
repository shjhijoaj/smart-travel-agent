import pytest
from api.main import final_answer, budget_warnings


@pytest.mark.parametrize('raw,expected', [
    ('<think>内部分析</think>## 每日行程\n最终方案', '## 每日行程\n最终方案'),
    ('<THINK>分析\n过程</THINK><!--provider-->结果', '结果'),
    ('<think>未结束的推理', ''),
    ('最终正文', '最终正文'),
    ('<think>一</think><think>二</think>正文', '正文'),
])
def test_final_answer(raw, expected):
    assert final_answer(raw) == expected


def test_range_over_budget_is_flagged():
    assert budget_warnings('| 合计 | 待确认，规划预留约3550-5900 |', '5000')
    assert not budget_warnings('| 合计 | 4,000 |', '5000')
    assert budget_warnings('| 合计 | 待确认 |', '5000')
    assert budget_warnings('没有预算表', '5000')
