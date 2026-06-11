# DDL Command Center

> 欢迎各位pkuer来到 **DDL作战指挥中心**  
> 这是一个集教学网代办任务、学期课程表、个人 TODO LIST 与 AI 助手于一体的本地桌面应用,由 **Roast_Spider 小组** 出品。

---

## 主要功能

- 📋 **任务管理**：
  支持一键同步教学网作业和自定义添加个性化任务。设定好估时和优先级后可使用AI小助手分析拆解任务。按照关联课程分类呈现和时间轴呈现的方式使得代办更加明晰。
- 🗓 **课程表**：从 PKU 门户 HTML 一键导入即可同步显示课程和ddl信息，同时支持单双周切换。
- 📝 **考试日历**：从课表 HTML 自动抽取期末考试。
- 🤖 **AI 智能创建**：用自然语言输入一段描述（比如"明天下午 3 点开组会，理科楼 206"）即可高效生成任务。
- 🔄 **同步教学网**：使用北大门户账号登陆即可。
- 📊 **进度统计**：用图表清晰呈现任务完成率和工作量分布。
- 🔔 **警报中心**：24h内截至/两个ddl相距过近/一天内ddl超标(>=3)等情况皆会触发预警，在任务管理界面右侧的提醒面板呈现。
- 💬 **AI 聊天**：接入 DeepSeek api key，即可使用AI智能服务。
- 💝 **联系作者页**：如果你有任何问题，可以直接联系作者。

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
| `PKU_OTP_CODE` | 否 | 启用 OTP（手机令牌）时填，否则留空 |
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

## 开发条款

- **GUI 不直接调 Repository / DB**：一律走 `AppFacade`
- **新功能优先加测试**：Manager 层用 stub repo，Parser 层用 fixture HTML
- **不要往 commit 里加 `Co-Authored-By: Claude`**
- 提交前跑一遍 `pytest`

---

## 联系方式

见应用内「联系作者」页 —— 赞赏码 + 邮箱

或直接通过邮箱联系：<enhuayang25@stu.pku.edu.cn>

---

## 许可

学生项目，内部学习用，未对外发布。
