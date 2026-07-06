"""Recitation (习题课) parsing — main-class week parity must NOT be polluted by
remarks, and remarks like '习题课双周周一10~11节' must produce their own slots."""
from __future__ import annotations


def _parse(html: str):
    from app.parsers.portal_schedule_parser import parse_portal_import
    return parse_portal_import(html)


def _wrap_cell(cell_id: str, body: str, *, color: str = "lightcoral") -> str:
    """Wrap a cell into the surrounding table structure used in the real HTML."""
    return f'''
    <html><body><table>
    <tr><td class="td-compact" id="{cell_id}" valign="top" style="background-color: {color};">
    <div style="line-height:16px;"><span style="font-size:12px;">{body}</span></div>
    </td></tr>
    </table></body></html>
    '''


def test_main_class_week_type_unaffected_by_remark_double_week():
    """线代 main lecture is every-week; '双周' inside the remark must not flip
    the main slot to even-week."""
    body = (
        "线性代数A (II)(主)<br>"
        "上课信息：1-15周 每周 理教201 教师：丁一文 "
        "备注：习题课双周周一10~11节，教室：三教208、二教315、二教317<br>"
        "考试信息：20260624 星期三 上午 二教107"
    )
    result = _parse(_wrap_cell("wed1", body))
    main_slots = [s for s in result["slots"] if not s.get("is_recitation")]
    assert len(main_slots) == 1
    assert main_slots[0]["week_type"] == "all"
    assert main_slots[0]["weekday"] == 3  # Wednesday
    assert main_slots[0]["location"] == "理教201"


def test_recitation_slot_emitted_for_double_week_remark():
    body = (
        "线性代数A (II)(主)<br>"
        "上课信息：1-15周 每周 理教201 教师：丁一文 "
        "备注：习题课双周周一10~11节，教室：三教208、二教315、二教317<br>"
        "考试信息：20260624 星期三 上午 二教107"
    )
    result = _parse(_wrap_cell("wed1", body))
    rec = [s for s in result["slots"] if s.get("is_recitation")]
    # 10-11节 = 2 slots (period 10 + period 11), both Monday, even-week.
    assert len(rec) == 2
    for r in rec:
        assert r["weekday"] == 1
        assert r["week_type"] == "even"
        assert r["title"].startswith("线性代数")
        assert "习题课" in r["title"]
        assert r["location"] == "三教208"
    assert {r["period"] for r in rec} == {10, 11}


def test_recitation_slot_emitted_for_every_week_remark():
    body = (
        "高等数学A（二）(主)<br>"
        "上课信息：1-15周 每周 二教205 教师：刘培东 "
        "备注：习题课每周三10-11节，教室：三教306、一教303、一教308<br>"
        "考试信息：20260618 星期四 上午 二教105"
    )
    result = _parse(_wrap_cell("tue1", body))
    rec = [s for s in result["slots"] if s.get("is_recitation")]
    assert len(rec) == 2
    for r in rec:
        assert r["weekday"] == 3  # Wednesday
        assert r["week_type"] == "all"
        assert "习题课" in r["title"]
        assert r["location"] == "三教306"


def test_remark_without_recitation_keyword_yields_no_extra_slot():
    """'与"程序设计与算法"互斥' is just a note, not a recitation."""
    body = (
        "程序设计实习(主)<br>"
        "上课信息：1-15周 每周 二教405 教师：刘家瑛 "
        "备注：与\"程序设计与算法\"、\"软件设计实践\"互斥<br>"
        "考试信息：20260626 星期五 下午 "
    )
    result = _parse(_wrap_cell("wed3", body))
    rec = [s for s in result["slots"] if s.get("is_recitation")]
    assert rec == []
    main_slots = [s for s in result["slots"] if not s.get("is_recitation")]
    assert len(main_slots) == 1
    assert main_slots[0]["week_type"] == "all"


def test_recitation_dedup_across_multi_cell_appearances():
    """The main course shows up in many cells (one per period it meets each
    week), but the recitation should only be emitted once per unique
    (course, weekday, period) tuple."""
    # Two cells, same course (linear algebra appears Wed periods 1 and 2).
    body = (
        "线性代数A (II)(主)<br>"
        "上课信息：1-15周 每周 理教201 教师：丁一文 "
        "备注：习题课双周周一10~11节，教室：三教208、二教315、二教317<br>"
        "考试信息：20260624 星期三 上午 二教107"
    )
    html = f'''
    <html><body><table>
      <tr>
        <td class="td-compact" id="wed1"><div><span>{body}</span></div></td>
        <td class="td-compact" id="wed2"><div><span>{body}</span></div></td>
      </tr>
    </table></body></html>
    '''
    result = _parse(html)
    rec = [s for s in result["slots"] if s.get("is_recitation")]
    # Should be exactly 2 slots (period 10 + period 11), NOT 4.
    assert len(rec) == 2
