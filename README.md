<div align="center">

# 🕷️ DDL Command Center 🕷️


**面向白鲸大学学生的 DDL 作战指挥中心**
教学网作业 · 课程表 · 考试日历 · 个人 TODO · AI 助手 ——
全部整合到一个本地桌面应用。

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52.svg)](https://www.qt.io/qt-for-python)
[![Tests](https://img.shields.io/badge/tests-186%20passing-brightgreen.svg)](#-testing)
[![License](https://img.shields.io/badge/license-Roast__Spider%20Internal-lightgrey.svg)](#-license)

[GitHub](https://github.com/BBBBBig-Spider/DDL-Center) · [Issues](https://github.com/BBBBBig-Spider/DDL-Center/issues)

</div>

---

## 📑 Table of Contents

- [🕷️ DDL Command Center 🕷️](#️-ddl-command-center-️)
  - [📑 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🚀 Quick Start](#-quick-start)
  - [⚙️ Configuration](#️-configuration)
  - [📥 课表导入](#-课表导入)
  - [🏗 Architecture](#-architecture)
  - [🧪 Testing](#-testing)
  - [🗺 Roadmap](#-roadmap)
  - [🤝 Contributing](#-contributing)
  - [📜 License](#-license)
  - [🙋 Contact](#-contact)

---

## ✨ Features

- **任务管理** — 教学网作业一键同步、自定义任务录入；估时、优先级、AI 拆解；按课程分类与时间轴双视图
- **课程表** — 从北大门户 HTML 一键导入；周视图 / 单双周切换；DDL 红线、当前时间蓝线、考试一并展示
- **考试日历** — 课表 HTML 中自动抽取期末考试场次与地点
- **AI 智能创建** — 自然语言描述（如 *"明天下午 3 点开组会，理科楼 206"*）一句话生成任务/课程/考试
- **教学网同步** — IAAA OAuth 登录，三桶分流（逾期丢弃 / AI 兜底 / 入库去重），不会覆盖你已编辑的字段
- **进度统计** — 完成率、工作量分布，matplotlib 嵌入 Qt 渲染
- **警报中心** — 24h 截止、DDL 拥堵、任务超载等多场景预警
- **AI 聊天** — 内嵌 DeepSeek 助手，自动携带本地 task 上下文
- **通用设置** — 主题色、当前时间线颜色等可配置项，持久化到本地

---


## 🚀 Quick Start

```bash
git clone https://github.com/BBBBBig-Spider/DDL-Center.git
cd DDL-Center

# 建议使用虚拟环境
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env                # 编辑 .env，填入凭据

python -m app.main
```

首次启动会在 `data/ddl_center.db` 自动建库。

> **贡献者请额外执行一次**：
> ```bash
> git config core.hooksPath .githooks
> ```
> 这会启用本地 pre-commit 钩子，自动拦截把头像 / 主题 / 同步缓存等**本地用户状态**误 push 到云端的行为。

---

## ⚙️ Configuration

凭据与密钥统一从 `.env` 读取。

| 变量 | 必填 | 默认 | 说明 |
|---|:---:|---|---|
| `PKU_USERNAME` | 同步必填 | — | 学号 |
| `PKU_PASSWORD` | 同步必填 | — | IAAA 密码 |
| `PKU_OTP_CODE` | 可选 | 空 | 启用手机令牌时填 |
| `DEEPSEEK_API_KEY` | AI 必填 | — | [DeepSeek](https://platform.deepseek.com/) API Key |
| `DEEPSEEK_MODEL` | 可选 | `deepseek-chat` | 模型名 |
| `AI_DAILY_TOKEN_LIMIT` | 可选 | `inf` | 每日 token 上限；正整数生效 |

---

## 📥 课表导入

应用支持两种课表导入方式：

**A. PKU 门户 HTML（推荐）**

1. 浏览器登录 [`https://portal.pku.edu.cn/publicQuery/#/myCourseTable`](https://portal.pku.edu.cn/publicQuery/#/myCourseTable)
2. 右键 → 另存为 → **仅 HTML**
3. 应用内「课程表」页 →「导入课表」→ 选择该 HTML

会自动识别课表 + 期末考试（含紧凑格式 `20260618 星期四 下午 二教105`）。

**B. JSON**（手写或导出）

```json
{
  "exam_week_start": "2026-06-15",
  "exam_week_end": "2026-06-28",
  "slots": [
    {
      "title": "高等数学", "weekday": 1,
      "start_time": "08:00", "end_time": "09:50",
      "location": "理教303",
      "start_week": 1, "end_week": 16, "week_type": "all"
    }
  ],
  "exams": [
    {
      "name": "高等数学考试",
      "start_time": "2026-06-20 09:00", "end_time": "2026-06-20 11:00",
      "location": "理教303", "exam_type": "final"
    }
  ]
}
```

---

## 🏗 Architecture

5 层职责分明：**GUI → AppFacade → Manager → Repository → SQLite / Network**

```
GUI ──► AppFacade ──► [TaskManager, ScheduleManager, ExamManager,
                       AlertManager, AIAssistantManager, SyncManager, ...]
                          │
                          ▼
                      Repositories
                          │
                          ▼
                       SQLite + 教学网 / IAAA HTTP
```

主要目录：

```
app/
├─ main.py            应用入口（DI 装配）
├─ config.py          全局常量、env 解析
├─ gui/               PySide6 窗口与组件
├─ managers/          业务逻辑（AppFacade 是唯一对 GUI 入口）
├─ models/            纯数据类
├─ repositories/      SQLite CRUD（每实体一个）
├─ network/           IAAA 登录、教学网 / LLM 客户端、KeyStore
├─ parsers/           HTML / JSON 解析（DDL、课表、考试）
├─ database/          DatabaseManager + schema.sql
├─ services/          凭据存储等跨层服务
└─ utils/             时间 / 校验 / CSV 工具

tests/                pytest 用例
data/                 SQLite DB 与抓取缓存（gitignored）
docs/                 设计文档与截图
scripts/              调试脚本（debug_sync.py 等）
```

完整设计、数据模型、PKU IAAA OAuth 流程、AI 兜底机制等详见仓库外的 [`项目架构文档.md`](../项目架构文档.md)。

---

## 🧪 Testing

```bash
pytest tests/ -q
```

当前 **186 passed**。覆盖范围：

- Manager 全部用 stub repository 注入测试
- Repository 直跑真实 SQLite
- Parser 用 fixture HTML 做回归
- 同步流程的三桶分流 + AI 兜底 + 不覆盖用户编辑
- GUI 关键交互（周次切换、当前时间线、设置面板）

---

## 🗺 Roadmap

- [x] 教学网作业三桶分流 + AI 兜底
- [x] 北大门户课表 HTML 导入（含考试紧凑格式）
- [x] 当前时间指示线 + 周次快捷切换
- [x] 通用设置侧栏（颜色配置）
- [ ] 任务依赖图（pre-req chains）
- [ ] 番茄钟 / 专注计时
- [ ] macOS / Linux 兼容性测试
- [ ] PyInstaller 打包 + 自动更新

---

## 🤝 Contributing

我们使用 `main` / `dev` / `feature/*` 三层分支：

1. 从 `dev` 切出 `feature/<your-feature>` 分支
2. 提交前跑 `pytest tests/ -q`，确保不破坏现有用例
3. PR 入 `dev`，code review 后由维护者并入 `main`

代码约定：

- GUI 一律通过 `AppFacade` 调用业务，**不**直接访问 Repository / DB
- 新功能优先加测试（Manager 用 stub repo，Parser 用 fixture）

---

## 📜 License

本项目目前为 **Roast_Spider 小组** 的内部学生项目，未公开发布。
若有任何使用、转载、改写需求，请通过下方联系方式与我们协商。

---

## 🙋 Contact

- 提交 Issue / 反馈：[GitHub Issues](https://github.com/BBBBBig-Spider/DDL-Center/issues)
- 应用内「联系作者」页 —— 赞赏码 + 作者邮箱

---

<div align="center">

Made with Big 🕷️ and Little 🕷️ by <strong>Roast_Spider 小组</strong>

</div>
