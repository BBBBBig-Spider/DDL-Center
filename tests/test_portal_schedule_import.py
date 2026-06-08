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
