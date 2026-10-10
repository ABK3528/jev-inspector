# Jev-Inspector: Autonomous AI-Powered Web Synthetic Monitoring & Error Hunting

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Playwright-Chromium-green?logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/AI_Engine-TypeSafe_Jev_System_One-purple" alt="TypeSafe Jev">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Coverage-32_Tests_Passing-brightgreen" alt="Tests">
</p>

---

## 📌 为什么需要 Jev-Inspector？传统线上巡检的死局

线上巡检（Synthetic Monitoring / 拨测）是保障生产系统稳定性的核心手段。然而，当前业界无论是基于 **Playwright / Cypress** 编写脚本，还是采购 **Checkly / Datadog Synthetics**，都面临难以逾越的工程瓶颈：

1. **写不完的脚本**：企业内部 Admin 管理后台、CRM、复杂 SaaS 系统包含成百上千个表单与页面，为每一个交互手写 E2E 测试脚本成本极高，版本稍有重构脚本便频繁失效。
2. **抓不住的静默崩溃**：大量前端单页应用（SPA）在接口报 500、400 或出现异常时，页面并不会直接 404，而是弹出一个短暂的 Toast 提示（如“网络开小差”、“系统错误”）。传统 HTTP 探活完全无法感知此类故障。
3. **断言的误报地狱**：简单的文字正则匹配常常将“操作成功”、“提示：请注意保存”等良性通知误判为故障，产生漫天告警噪音。

**Jev-Inspector** 彻底改变了这一切——**零人工手写脚本，输入 URL 即刻开启全自主探索与智能故障捕获**。

---

## 🚀 核心架构与创新突破

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Jev-Inspector 生产级巡检体系                       │
├────────────────────────────────────────────────────────────────────────┤
│  1. 调度编排层 (scheduler.py / run_inspection.py)                      │
│     • ThreadPool 多站点高并发隔离调度                                   │
│     • 指数退避重试 (Exponential Backoff) + 连续失败智能熔断             │
│     • SQLite 历史结果自动持久化 (ResultStore)                           │
│     • HTTP 探针服务 (/health 存活检测, /metrics Prometheus指标)          │
│                                                                        │
│  2. 执行与决策层 (crawler.py / flow_engine.py / jev_client.py)          │
│     • 双模驱动：预设确定性业务链 (FlowExecutor) + AI 广度探索 (Crawler)  │
│     • DOM 结构指纹去重 (Flex/Grid/Card/Table 行模式归一化)               │
│     • 破坏性动作拦截器 (Destructive Action Guard: 防误触登出/删库/注销)   │
│     • Jev AI 决策原语 (noul 判定 + choice 归类 + score 严重度定级)       │
│                                                                        │
│  3. 可观测与告警层 (alert_manager.py / generate_report.py)             │
│     • 多通道富文本告警：飞书卡片 / 钉钉 Markdown / 企业微信 / Slack    │
│     • Prometheus 指标实时生成 (.prom & /metrics)                        │
│     • 交互式 HTML 巡检可视化大屏 + 故障现场截图留存                     │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. 零脚本 AI 主动遍历与结构去重
无需预先录制操作。引擎基于真实 Chromium 实时解析 DOM 树，提取所有按钮、表单、输入框、下拉菜单等交互元素。
- **结构指纹（Structural Fingerprinting）**：自动提取元素父级容器路径，将列表项（`li`）、表格行（`tr`）、卡片网格（`card`）归一化，自动规避对同类数据的大量重复点击。
- **语义去重（Semantic Dedup）**：调用 Jev 智能研判控件语义，过滤功能冗余的重复项。

### 2. 多维故障证据链 + AI 智能研判
每次交互后，引擎秒级聚合三大维度的现场证据：
- **DOM 视窗层**：监听 DOM 中弹出的 Toast、Banner、Modal 弹窗与 Alert。
- **运行时日志层**：实时监听 Browser Console 日志，捕捉 Unhandled Rejections 与 JavaScript 运行时异常。
- **网络协议层**：网络代理拦截实时捕捉 4xx / 5xx HTTP 接口报错。

将证据输入 **Jev System One 决策模型**：
- **`noul`（二元确定度）**：秒级判定该反馈是否代表真实故障，精准过滤 WebGL 弃用警告、普通通知或成功提示。
- **`choice`（多标签分类）**：精确归类为 `network_error`（网络断开/超时）、`system_error`（后端5xx/系统崩溃）、`request_error`（400/403/参数异常）或 `browser_noise`（良性噪音）。
- **`score`（严重度评分）**：量化故障影响面，严重问题自动截屏存证。

### 3. 双模驱动：核心业务链 (Flow) + 广度自主探索
除了自主探索，框架支持通过 `flow_engine.py` 声明核心业务链路（如：打开登录页 → 输入账号密码 → 点击登录 → 验证控制台欢迎语），并支持：
- 丰富的规则断言：`text_contains`、`visible`、`title_matches`、`url_matches`。
- **SLA 耗时红线**：定义单链路执行时延上限，超时即报 SLA 违约。

### 4. 专为生产而生的可靠性工程
- **破坏性操作安全防御**：正则安全沙箱实时识别并跳过“退出登录”、“注销账号”、“清空数据”、“Delete”等敏感按钮。
- **域内锁定与越界自动回跳**：防止爬虫跳出业务域，确保巡检始终在受控边界内。
- **多通道生产告警**：原生适配飞书交互卡片、钉钉 Markdown 告警、企业微信机器人、Slack Webhook。
- **云原生可观测性**：直接生成 Prometheus 指标文件，并常驻暴露 `/metrics` 与 `/health` HTTP 接口。

---

## 🛠️ 快速上手

### 1. 环境准备与依赖安装
```bash
git clone https://github.com/ABKtester/jev-inspector.git
cd jev-inspector

# 安装 Python 依赖与 Playwright 浏览器内核
pip install playwright
playwright install chromium
```

### 2. 导出 Jev 决策模型 API Key（可选）
> *注：框架内置健壮的本地降级规则引擎。未配置 API Key 时系统会自动切换至本地规则库，核心巡检与报错拦截能力不受影响。*
```bash
export TYPESAFE_API_KEY="your_typesafe_api_key"
```

### 3. 运行单站点智能巡检
```bash
# 启动智能巡检（自动遍历、错误检测、安全防御）
python3 main.py --url https://httpbin.org/forms/post --max-actions 20

# 使用生产配置文件运行并指定飞书告警
python3 main.py --config inspection_config.sample.json \
  --webhook-url "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
  --webhook-type feishu
```

### 4. 运行多站点并发编排与健康常驻服务
```bash
# 并发巡检多个业务站点，并在 8089 端口启动存活探针与 Prometheus Metrics 服务
python3 run_inspection.py --config sites_config.sample.json --serve --port 8089
```

服务启动后，即可通过 HTTP 接口查询：
- **健康检测探针**：`curl http://localhost:8089/health`（返回 200/503 及聚合健康状态）
- **Prometheus 指标**：`curl http://localhost:8089/metrics`
- **巡检历史记录**：`curl http://localhost:8089/history`

### 5. 查询最近一次巡检结果 (CLI)
```bash
python3 run_inspection.py --health
```

---

## 📊 配置文件示例

### 单站点巡检与关键业务流配置 (`inspection_config.sample.json`)
```json
{
  "target_url": "https://the-internet.herokuapp.com/status_codes",
  "max_actions": 25,
  "headless": true,
  "action_timeout_ms": 4000,
  "page_load_timeout_ms": 20000,
  "wait_after_action": 0.8,
  "use_jev_dedup": true,
  "report_json_path": "traversal_report.json",
  "report_html_path": "traversal_report.html",
  "screenshot_dir": "screenshots",
  "destructive_keywords": [
    "注销", "登出", "退出登录", "删除账号", "清空数据库",
    "drop table", "format disk", "delete account", "sign out", "logout"
  ],
  "flows": [
    {
      "name": "关键状态码冒烟链路",
      "start_url": "https://the-internet.herokuapp.com/status_codes",
      "sla_max_duration_seconds": 10.0,
      "steps": [
        {
          "action": "click",
          "selector": "a[href='status_codes/200']",
          "description": "点击 200 状态码链接"
        },
        {
          "action": "assert",
          "selector": ".example p",
          "assert_type": "text_contains",
          "expected": "This page returned a 200 status code",
          "description": "验证页面成功返回 200 说明"
        }
      ]
    }
  ],
  "alert": {
    "enabled": false,
    "webhook_url": null,
    "webhook_type": "feishu",
    "min_severity_score": 0.5
  }
}
```

---

## 📈 与行业竞品全方位横向对比

| 评估维度 | Datadog Synthetics | Checkly | Grafana k6 Browser | Sentry | **Jev-Inspector (本项目)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **交互与探测方式** | 需人工手写/录制脚本 | 需手写 Playwright 脚本 | 需手写 k6 脚本 | 被动 SDK 埋点 | **零脚本 AI 全自主遍历 + 结构去重** |
| **AI 智能决策** | ❌ 无 | ❌ 无 | ❌ 无 | 仅支持错误聚合 | **✅ Jev 原语研判、归类与严重度量化** |
| **故障捕获维度** | 依赖脚本断言 | 依赖脚本断言 | 依赖脚本断言 | 运行时捕获 | **DOM 视窗 + 控制台日志 + 网络 4xx/5xx 三重证据链** |
| **关键业务流支持** | ✅ 支持 | ✅ 支持 | ✅ 支持 | ❌ 不支持 | **✅ 支持 (FlowEngine 配合 SLA 校验)** |
| **多站点并发与重试** | ✅ 支持 (SaaS) | ✅ 支持 (SaaS) | ✅ 分布式 | N/A | **✅ 线程池并发 + 指数退避重试 + 熔断** |
| **告警通道** | 欧美通道为主 | 欧美通道为主 | Grafana Alerting | Webhook | **飞书卡片 / 钉钉 Markdown / 企微 / Slack** |
| **私有化与合规** | ❌ 仅 SaaS 托管 | ❌ 依赖云端调度 | ⚠️ 部分自建复杂 | ⚠️ 自建门槛高 | **✅ 100% 纯 Python 自托管，数据零出域** |

---

## 🧪 自动化测试套件

项目拥有完整的单元测试与集成测试覆盖，包含本地 HTTP 模拟服务器端到端闭环验证：

```bash
python3 -m unittest discover -p "test_*.py"
```

输出结果：
```text
Ran 32 tests in 9.72s
OK
```

- **`test_flow.py`**：业务流执行引擎、各种规则断言及 SLA 时延违约测试。
- **`test_scheduler.py`**：并发调度器、SQLite 结果持久化、`/health`、`/metrics` HTTP 服务测试。
- **`test_inspection.py`**：配置覆盖、安全防误触过滤、结构去重及本地 Mock 端到端闭环。

---

## 🚢 CI/CD 与 Kubernetes 生产部署

### Linux Crontab 定时巡检
```bash
# 每 15 分钟执行一次多站点巡检，失败自动触发告警
*/15 * * * * cd /opt/jev-inspector && python3 run_inspection.py --config sites_config.sample.json --fail-on-error >> /var/log/inspector.log 2>&1
```

### Docker 容器化运行
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-noble
WORKDIR /app
COPY . .
RUN pip install playwright && playwright install chromium
ENV TYPESAFE_API_KEY=your_api_key
CMD ["python3", "run_inspection.py", "--config", "sites_config.sample.json", "--serve", "--port", "8089"]
```

---

## 📄 开源许可证

本项目采用 [Apache-2.0](LICENSE) 许可证开源。欢迎提交 Issue 与 Pull Request！
