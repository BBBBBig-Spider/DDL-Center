from app.parsers.portal_schedule_parser import parse_portal_html, parse_portal_import


def test_portal_import_parses_schedule_exams_and_exam_week():
    html = """
    <html>
      <body>
        <p>考试周：2026-06-15 至 2026-06-28</p>
        <table>
          <tr>
            <td id="mon1">
              高等数学(一班)
              上课信息：1-16周 每周 理教303 教师：张老师
              考试信息：2026-06-20 09:00-11:00 理教303
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    parsed = parse_portal_import(html)

    assert len(parsed["slots"]) == 1
    assert parsed["slots"][0]["title"] == "高等数学"
    assert parsed["slots"][0]["weekday"] == 1
    assert parsed["exam_week_start"] == "2026-06-15"
    assert parsed["exam_week_end"] == "2026-06-28"
    assert len(parsed["exams"]) == 1
    assert parsed["exams"][0]["name"] == "高等数学考试"
    assert parsed["exams"][0]["start_time"] == "2026-06-20T09:00"
    assert parsed["exams"][0]["end_time"] == "2026-06-20T11:00"
    assert parsed["exams"][0]["location"] == "理教303"


def test_parse_portal_html_keeps_legacy_slots_only_contract():
    html = """
    <table>
      <tr><td id="wed5">大学英语(一班)\n考试信息：2026-06-21 14:00-16:00 二教101</td></tr>
    </table>
    """

    slots = parse_portal_html(html)

    assert isinstance(slots, list)
    assert len(slots) == 1
    assert "exams" not in slots[0]


def test_parse_portal_import_compact_exam_format():
    """PKU portal compact form: '20260618 星期四 下午 二教105' (no clock)."""
    html = """
    <table>
      <tr>
        <td id="thu1">高等数学A（二）<br>
        上课信息：1-15周 每周 理教205<br>
        考试信息：20260618 星期四 下午 二教105</td>
      </tr>
    </table>
    """
    parsed = parse_portal_import(html)
    assert len(parsed["exams"]) == 1
    exam = parsed["exams"][0]
    # _CLASS_SUFFIX_RE strips trailing "（...）" — pre-existing behavior.
    assert exam["course_name"] == "高等数学A"
    # 下午 → 13:00-17:00 window
    assert exam["start_time"] == "2026-06-18T13:00"
    assert exam["end_time"] == "2026-06-18T17:00"
    assert exam["location"] == "二教105"
    assert exam["exam_type"] == "final"


def test_parse_portal_import_dedupes_exam_repeats():
    """Same course in N cells should produce ONE exam, not N copies."""
    html = """
    <table>
      <tr>
        <td id="mon1">微积分<br>
        上课信息：1-15周 每周 理教205<br>
        考试信息：20260618 星期四 上午 理教1</td>
        <td id="mon2">微积分<br>
        上课信息：1-15周 每周 理教205<br>
        考试信息：20260618 星期四 上午 理教1</td>
        <td id="tue1">微积分<br>
        上课信息：1-15周 每周 理教205<br>
        考试信息：20260618 星期四 上午 理教1</td>
      </tr>
    </table>
    """
    parsed = parse_portal_import(html)
    assert len(parsed["exams"]) == 1


def test_parse_portal_import_accepts_xingqi_qi_for_sunday():
    """PKU portal uses '星期七' (literally weekday 7) for Sundays — must parse."""
    html = """
    <table>
      <tr>
        <td id="sun1">概率统计<br>
        上课信息：1-15周 每周 理教205<br>
        考试信息：20260621 星期七 上午 理教307</td>
      </tr>
    </table>
    """
    parsed = parse_portal_import(html)
    assert len(parsed["exams"]) == 1
    exam = parsed["exams"][0]
    assert exam["start_time"] == "2026-06-21T08:00"
    assert exam["location"] == "理教307"


def test_parse_portal_import_legacy_exam_format_still_works():
    """Pre-existing 'YYYY-MM-DD HH:MM-HH:MM 地点' form must still parse."""
    html = """
    <table>
      <tr>
        <td id="wed1">数据结构<br>
        上课信息：1-15周 每周 理教303<br>
        考试信息：2026-06-20 09:00-11:00 理教303</td>
      </tr>
    </table>
    """
    parsed = parse_portal_import(html)
    assert len(parsed["exams"]) == 1
    exam = parsed["exams"][0]
    assert exam["start_time"] == "2026-06-20T09:00"
    assert exam["end_time"] == "2026-06-20T11:00"
    assert exam["location"] == "理教303"
