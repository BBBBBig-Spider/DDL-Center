# DDL Command Center

> 北京大学学生的 DDL 作战指挥中心 —— 把教学网作业、课程表、考试、个人 TODO 与 AI 助手整合到一个本地桌面应用里。

由 **Roast_Spider 小组** 出品。详细架构请见仓库外的 `项目架构文档.md`。

---

## 功能速览

- 📋 **任务管理**：新建/编辑/完成/归档，支持课程关联、优先级、估时
- 🗓 **课程表**：周视图渲染，支持从 PKU 门户 HTML 一键导入（含考试）
- 📝 **考试日历**：从课表 HTML 自动抽取期末考试
- 🤖 **AI 智能创建**：粘一段中文描述（"明天下午 3 点开组会，理科楼 206"）即生成任务/课程/考试
- 🔄 **同步教学网**：IAAA 登录 → 抓「课程作业」页 → 三桶分流（逾期丢弃 / AI 兜底 / 直接入库），不会覆盖你已编辑的字段
- 📊 **进度统计**：完成率、工作量分布（matplotlib 嵌 Qt）
- 🔔 **警报中心**：24h / 72h / 一周内将到期任务、本周拥堵预警
- 💬 **AI 聊天**：内嵌 DeepSeek 助手，携带你的本地 task 上下文
- 💝 **联系作者页**：赞赏码 + 作者邮箱

---

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 | Python 3.10+ |
| GUI | PySide6（Qt for Python） |
| 存储 | SQLite |
| HTTP | requests + beautifulsoup4 + lxml |
| 加密（IAAA RSA） | pycryptodome |
| 图表 | matplotlib |
| AI | openai SDK + DeepSeek 兼容协议 |
| Secret | python-dotenv（首选） / keyring（备选） |
| 测试 | pytest（22 文件 / 169 case） |

---

## 仓库结构

```
DDL-Center/
├─ app/
│  ├─ main.py                    # 入口
│  ├─ config.py                  # 全局常量、env 解析
│  ├─ database/                  # SQLite + schema.sql
│  ├─ models/                    # Task / Course / Exam / ScheduleSlot / Alert / ...
│  ├─ repositories/              # 每个实体一个 CRUD
│  ├─ managers/                  # 业务逻辑 + AppFacade（GUI 唯一入口）
│  ├─ network/                   # IAAA 登录、教学网、LLM、KeyStore
│  ├─ parsers/                   # DDL / 课表 / 考试 HTML 解析
│  ├─ gui/                       # PySide6 窗口 + 组件 + 资源
│  ├─ services/                  # 跨层服务（凭据存储等）
│  └─ utils/                     # 时间/校验/CSV 工具
├─ tests/                        # pytest 用例
├─ data/                         # SQLite DB（gitignore） + 抓取缓存
├─ docs/                         # 设计文档
├─ scripts/                      # debug_sync.py 等调试脚本
├─ requirements.txt
├─ .env.example                  # 环境变量模板
├─ .gitignore
└─ README.md
```

---

## 快速开始

```bash
# 1. 克隆并进目录
cd DDL-Center

# 2. 安装依赖（建议虚拟环境）
pip install -r requirements.txt

# 3. 复制 env 模板并填入凭据
cp .env.example .env
#   编辑 .env，填上 PKU 学号/密码、DeepSeek API key

# 4. 启动 GUI
python -m app.main
```

启动后会自动创建 `data/ddl_center.db`。

---

## 环境变量（`.env`）

| 变量 | 必填 | 说明 |
|---|---|---|
| `PKU_USERNAME` | 是（仅同步教学网时） | 学号 |
| `PKU_PASSWORD` | 是 | IAAA 密码 |
| `PKU_OTP_CODE` | 否 | 启用 OTP 时填，否则留空 |
| `DEEPSEEK_API_KEY` | 是（仅 AI 功能时） | DeepSeek key |
| `DEEPSEEK_MODEL` | 否 | 默认 `deepseek-chat` |
| `AI_DAILY_TOKEN_LIMIT` | 否 | 默认无限。设正整数可恢复每日上限 |

凭据/密钥从不写入仓库 —— `.env` 已 gitignore。

---

## PKU IAAA 登录原理

1. `GET https://iaaa.pku.edu.cn/iaaa/getPublicKey.do?appId=blackboard` → 拿 RSA 公钥
2. PKCS#1 v1.5 加密密码（`pycryptodome`）
3. `POST oauthlogin.do` → 拿 `token`
4. 重定向 `course.pku.edu.cn/.../campusLogin?token=<token>` 完成 SSO

完整代码见 `app/network/auth_client.py`。

---

## 课表导入

支持两种格式：

**A. JSON**（手写或导出）
```json
{
  "exam_week_start": "2026-06-15",
  "exam_week_end": "2026-06-28",
  "slots": [{ "title": "高等数学", "weekday": 1, "start_time": "08:00", "end_time": "09:50", "location": "理教303", "start_week": 1, "end_week": 16, "week_type": "all" }],
  "exams":  [{ "name": "高等数学考试", "start_time": "2026-06-20 09:00", "end_time": "2026-06-20 11:00", "location": "理教303", "exam_type": "final" }]
}
```

**B. PKU 门户课表 HTML**
- 访问 `https://portal.pku.edu.cn/publicQuery/#/myCourseTable` → 右键 → 另存为 → 仅 HTML
- 在「课程表」页 →「导入课表」→ 加载文件
- 同步抽取课表 + 考试（识别紧凑格式 `20260618 星期四 下午 二教105`）

---

## 测试

```bash
pytest tests/ -q
# 169 passed
```

---

## 开发约定

- **GUI 不直接调 Repository / DB**：一律走 `AppFacade`
- **新功能优先加测试**：Manager 层用 stub repo，Parser 层用 fixture HTML
- **不要往 commit 里加 `Co-Authored-By: Claude`**
- 提交前跑一遍 `pytest`

分支：
- `main` 稳定
- `dev` 集成
- `feature/*` 单独功能分支，PR 入 `dev`

---

## 联系

应用内：「联系作者」页 —— 赞赏码 + 邮箱

邮箱：<enhuayang25@stu.pku.edu.cn>

---

## 许可

学生项目，内部学习用，未对外发布。
