# tests/test_course_repository.py
"""
CourseRepository 单元测试。
使用真实 DatabaseManager + 内存数据库，避免重复维护 schema。
"""
from __future__ import annotations

import unittest

from app.database.database_manager import DatabaseManager
from app.models.course import Course
from app.repositories.course_repository import CourseRepository


class TestCourseRepository(unittest.TestCase):
    def setUp(self) -> None:
        """每个测试运行前都执行：准备干净的内存数据库 + Repository。"""
        self.db_manager = DatabaseManager(":memory:")
        self.db_manager.initialize_database()
        self.repo = CourseRepository(self.db_manager)

        self.sample_course = Course(
            name="编译原理",
            teacher="张老师",
            semester="2025-2026-1",
            external_id="BB_CS101",
            color="#4F81BD",
            source="manual",
            raw_payload="",
        )

    def tearDown(self) -> None:
        self.db_manager.close()

    # ─── 基本 CRUD ────────────────────────────────────────────

    def test_add_and_get_by_id(self) -> None:
        """测试添加课程并能通过 ID 获取。"""
        course_id = self.repo.add(self.sample_course)
        self.assertIsNotNone(course_id)

        fetched = self.repo.get_by_id(course_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, course_id)
        self.assertEqual(fetched.name, "编译原理")
        self.assertEqual(fetched.teacher, "张老师")
        self.assertEqual(fetched.semester, "2025-2026-1")
        self.assertEqual(fetched.external_id, "BB_CS101")
        self.assertEqual(fetched.color, "#4F81BD")
        self.assertEqual(fetched.source, "manual")
        self.assertEqual(fetched.raw_payload, "")

    def test_get_by_id_not_found(self) -> None:
        """不存在的 id 应该返回 None。"""
        self.assertIsNone(self.repo.get_by_id(9999))

    def test_list_all_orders_by_id_asc(self) -> None:
        """list_all 应按 id 升序返回。"""
        first_id = self.repo.add(self.sample_course)
        second_id = self.repo.add(Course(name="数据结构", teacher="李老师"))

        courses = self.repo.list_all()
        self.assertEqual([c.id for c in courses], [first_id, second_id])
        self.assertEqual([c.name for c in courses], ["编译原理", "数据结构"])

    def test_list_all_empty(self) -> None:
        """空表 list_all 应返回空列表，不应报错。"""
        self.assertEqual(self.repo.list_all(), [])

    def test_update_course(self) -> None:
        """测试更新课程属性。"""
        course_id = self.repo.add(self.sample_course)

        course = self.repo.get_by_id(course_id)
        course.teacher = "王老师"
        course.color = "#FF0000"

        self.assertTrue(self.repo.update(course))

        updated = self.repo.get_by_id(course_id)
        self.assertEqual(updated.teacher, "王老师")
        self.assertEqual(updated.color, "#FF0000")

    def test_update_without_id_raises(self) -> None:
        """没有 id 的 course 调用 update 应该抛 ValueError。"""
        course = Course(name="未保存的课")
        with self.assertRaises(ValueError):
            self.repo.update(course)

    def test_update_nonexistent_returns_false(self) -> None:
        """更新不存在的 id 应返回 False，不应抛异常。"""
        course = Course(id=9999, name="不存在")
        self.assertFalse(self.repo.update(course))

    def test_delete_course(self) -> None:
        """测试删除课程后再次查询返回 None。"""
        course_id = self.repo.add(self.sample_course)

        self.assertTrue(self.repo.delete(course_id))
        self.assertIsNone(self.repo.get_by_id(course_id))

    def test_delete_nonexistent_returns_false(self) -> None:
        """删除不存在的 id 应返回 False。"""
        self.assertFalse(self.repo.delete(9999))

    # ─── find_by_external_id ──────────────────────────────────

    def test_find_by_external_id(self) -> None:
        """测试根据 external_id 查找课程（同步流程依赖此方法，仅匹配 source='sync'）。"""
        synced = Course(
            name="编译原理",
            teacher="张老师",
            semester="2025-2026-1",
            external_id="BB_CS101",
            color="#4F81BD",
            source="sync",
            raw_payload="",
        )
        self.repo.add(synced)

        found = self.repo.find_by_external_id("BB_CS101")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "编译原理")

    def test_find_by_external_id_ignores_manual(self) -> None:
        """source='manual' 的行不应被同步流程命中，即使 external_id 一致。"""
        self.repo.add(self.sample_course)
        self.assertIsNone(self.repo.find_by_external_id("BB_CS101"))

    def test_find_by_external_id_not_found(self) -> None:
        """不存在的 external_id 应返回 None。"""
        self.assertIsNone(self.repo.find_by_external_id("BB_NOT_EXIST"))

    def test_find_by_external_id_rejects_invalid(self) -> None:
        """空字符串或非字符串应抛 ValueError。"""
        with self.assertRaises(ValueError):
            self.repo.find_by_external_id("")
        with self.assertRaises(ValueError):
            self.repo.find_by_external_id(None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.repo.find_by_external_id(123)  # type: ignore[arg-type]

    # ─── 字段校验：add ────────────────────────────────────────

    def test_add_rejects_non_course(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.add("not a course")  # type: ignore[arg-type]

    def test_add_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.add(Course(name=""))
        with self.assertRaises(ValueError):
            self.repo.add(Course(name="   "))

    def test_add_rejects_bad_source(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.add(Course(name="bad source", source="api"))

    def test_add_rejects_non_string_teacher(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.add(Course(name="bad teacher", teacher=123))  # type: ignore[arg-type]

    def test_add_rejects_non_string_semester(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.add(Course(name="bad semester", semester=2025))  # type: ignore[arg-type]

    def test_add_rejects_non_string_external_id(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.add(Course(name="bad ext", external_id=42))  # type: ignore[arg-type]

    def test_add_rejects_empty_color(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.add(Course(name="bad color", color=""))

    def test_add_rejects_non_string_raw_payload(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.add(Course(name="bad payload", raw_payload=None))  # type: ignore[arg-type]

    def test_add_allows_external_id_none(self) -> None:
        """external_id 为 None 是合法值（手动创建的课程）。"""
        course_id = self.repo.add(Course(name="手动课", external_id=None))
        fetched = self.repo.get_by_id(course_id)
        self.assertIsNone(fetched.external_id)

    # ─── 字段校验：update ─────────────────────────────────────

    def test_update_rejects_non_course(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.update("not a course")  # type: ignore[arg-type]

    def test_update_rejects_empty_name(self) -> None:
        course_id = self.repo.add(self.sample_course)
        course = self.repo.get_by_id(course_id)
        course.name = ""
        with self.assertRaises(ValueError):
            self.repo.update(course)

    def test_update_rejects_bad_source(self) -> None:
        course_id = self.repo.add(self.sample_course)
        course = self.repo.get_by_id(course_id)
        course.source = "api"
        with self.assertRaises(ValueError):
            self.repo.update(course)

    # ─── 字段校验：get_by_id / delete ────────────────────────

    def test_get_by_id_rejects_non_int(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.get_by_id("1")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            self.repo.get_by_id(True)  # type: ignore[arg-type]

    def test_delete_rejects_non_int(self) -> None:
        with self.assertRaises(TypeError):
            self.repo.delete("1")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            self.repo.delete(False)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
