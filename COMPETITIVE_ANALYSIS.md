# Jev Web Inspection Framework — 行业对比分析与体系化架构报告

## 一、行业主流巡检/合成监控工具对比

| 维度 | Datadog Synthetic | Checkly | Grafana Synthetic (k6) | Sentry | **Jev Web Inspection** |
|:---|:---|:---|:---|:---|:---|
| **核心定位** | SaaS 端到端用户模拟 | Monitoring-as-Code (MaC) | 可观测性生态内浏览器拨测 | 运行时异常捕获（被动） | 自主交互式智能巡检引擎 |
| **浏览器引擎** | Chromium (托管) | Playwright (托管) | k6 + Chromium | N/A (SDK) | Playwright (自托管) |
| **交互方式** | 用户手写脚本 / 录制器 | 用户手写 Playwright 脚本 | 用户手写 k6 browser 脚本 | 自动 SDK 采集 | **零脚本自动化：AI 自动遍历 + 智能去重** |
| **AI 智能决策** | ❌ | ❌ | ❌ | 有 Issue Grouping | ✅ Jev AI：语义去重 + 故障分类 + 严重度评分 |
| **故障检测方式** | 断言 + HTTP 状态码 | 断言 + HTTP 状态码 | 断言 + HTTP 状态码 | 运行时崩溃/异常 | **DOM Toast/Alert + Console + Network 4xx/5xx + AI 聚合研判** |
| **多站点并发** | ✅ (SaaS) | ✅ (SaaS) | ✅ (分布式 k6) | N/A | ✅ ThreadPool 并发 + 重试退避 |
| **告警通道** | Slack/PagerDuty/Email 等 | Slack/Email/OpsGenie 等 | Grafana Alerting 全通道 | Slack/Email/Webhook | 飞书/钉钉/企业微信/Slack/通用 Webhook |
| **Prometheus 指标** | 内置 (SaaS) | 内置 (SaaS) | 原生集成 | Sentry Metrics | ✅ OpenMetrics `.prom` 文件 + `/metrics` HTTP 端点 |
| **CI/CD 退出码** | ✅ | ✅ | ✅ | ❌ | ✅ Exit Code 0/1 |
| **历史持久化** | 云端 SaaS | 云端 SaaS | 云端 SaaS | 云端 SaaS | ✅ 本地 SQLite + JSON 文件 |
| **部署模式** | SaaS (付费) | SaaS + 私有探针 (付费) | SaaS + 自托管 (部分付费) | SaaS (付费) | **完全自托管、开源、零外部依赖** |
| **适用场景** | 已有 SaaS 预算的云原生团队 | DevOps 团队 MaC | Grafana 全家桶用户 | 前端运行时错误回收 | **内网系统、无 SaaS 预算、需 AI 主动探索** |

---

## 二、本框架的真实差异化价值

### 2.1 独有核心价值："零脚本 AI 主动巡检"

行业几乎所有合成监控工具的共同前提是：**必须由人工预先编写 Playwright/k6/Selenium 测试脚本**。
- Datadog：必须在 Synthetics 界面录制或手写 Multi-Step Browser Test。
- Checkly：需要写 `checkly.config.ts`，用 Playwright 脚本描述步骤。
- Grafana k6：需写 `browser.newPage()` + locator 断言代码。

**本框架的核心差异**：
> 给定一个 URL 即可自动遍历页面上所有可交互控件，利用 AI（Jev System One）进行语义去重与故障分类，实现**零人工脚本**的主动探测。

**适用场景**：
- 内部管理后台（Admin Panel）有几十个页面、上百个表单，不可能一一手写 E2E 脚本。
- 线上版本频繁迭代，脚本维护成本极高。
- 想要"广覆盖、低成本"地发现页面崩溃、接口 500、Toast 异常。

### 2.2 多维故障聚合 + AI 研判

传统工具依赖用户手写的断言判定成功/失败。本框架同时从 DOM 视窗层、浏览器控制台层、网络请求层三个维度收集证据，提交给 Jev 模型进行 **noul(二元确定度) + choice(故障分类) + score(严重度)** 三维研判，能区分"正常 Toast（如操作成功）"与"系统级故障"。

### 2.3 完全私有化部署、合规友好

所有 SaaS 方案（Datadog/Checkly/Grafana Cloud）都要求将流量数据上传到第三方云端，对金融、政务、军工等合规敏感行业不适用。本框架：
- **完全运行在私有环境**，数据不出域。
- 巡检结果存储在本地 SQLite，指标通过 Prometheus 端点暴露。
- 告警通道对接国内主流 IM（飞书、钉钉、企业微信）。

---

## 三、当前框架仍然存在的缺陷与改进空间

### 已识别并已解决的缺陷（本轮已修复）

| 缺陷 | 状态 |
|:---|:---|
| 无配置文件支持，参数硬编码 | ✅ 已修复 (`config.py` + JSON + Env) |
| 无告警通道 | ✅ 已修复 (`alert_manager.py`) |
| 无 Prometheus 监控指标 | ✅ 已修复 (`.prom` 文件 + `/metrics` HTTP) |
| 无 CI/CD 退出码语义 | ✅ 已修复 (Exit 0/1) |
| 无多站点并发巡检 | ✅ 已修复 (`scheduler.py`) |
| 无重试与熔断机制 | ✅ 已修复 (指数退避 + 连续失败熔断) |
| 无历史持久化 | ✅ 已修复 (SQLite `ResultStore`) |
| 无健康检查端点 | ✅ 已修复 (`HealthCheckServer` /health /metrics /history) |
| Jev API 不可用时整个巡检崩溃 | ✅ 已修复 (本地 regex fallback) |
| 无法定义多步骤核心业务链路与 SLA | ✅ 已修复 (`flow_engine.py` + `FlowExecutor` + 断言体系) |
| 缺少自定义规则与断言校验 | ✅ 已修复 (text_contains / visible / title_matches / url_matches) |

### 已识别、待后续迭代的能力差距

| 缺陷 / 差距 | 优先级 | 说明 |
|:---|:---|:---|
| **视觉回归检测 (Visual Regression)** | P2 | 当前仅做功能交互与错误检测，缺少截图像素级/布局对比（业界：Percy/Applitools/Playwright `expect(screenshot).toMatchSnapshot()`）。 |
| **分布式探针 (Distributed Probes)** | P2 | 当前单机运行。生产级需要多地理位置探针并发拨测（如北京/上海/广州 同时巡检同一系统，对比各地延迟与可用性）。 |
| **Webhook 鉴权 (Signed Payload)** | P3 | 当前 Webhook 不支持 HMAC 签名验证，安全性依赖传输层 HTTPS。 |
| **Dashboard Web UI** | P3 | 当前 HTML 报告是静态文件。可考虑轻量 Web UI 查看历史巡检结果趋势、错误分布热力图等。 |

---

## 四、体系化架构总览

```
┌────────────────────────────────────────────────────────────────┐
│                  Jev Web Inspection System                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │  CLI / main.py  │    │ Config       │    │ Sites Config  │ │
│  │  (单站点入口)    │    │ (JSON/ENV)   │    │ (多站点配置)  │ │
│  └───────┬─────────┘    └──────┬───────┘    └──────┬────────┘ │
│          │                     │                    │          │
│          ▼                     ▼                    ▼          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           InspectionScheduler (scheduler.py)              │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │ │
│  │  │ ThreadPool  │  │ Retry/Backoff│  │ Circuit Breaker  │ │ │
│  │  │ Concurrency │  │ per site     │  │ (max failures)   │ │ │
│  │  └──────┬──────┘  └──────┬───────┘  └──────────────────┘ │ │
│  └─────────┼────────────────┼────────────────────────────────┘ │
│            │                │                                  │
│            ▼                ▼                                  │
│  ┌─────────────────────────────────────────────────┐          │
│  │       WebInspectionCrawler (crawler.py)          │          │
│  │                                                  │          │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │          │
│  │  │ Playwright │  │ DOM/Console│  │ Network     │ │          │
│  │  │ Browser    │  │ Error Trap │  │ 4xx/5xx     │ │          │
│  │  └─────┬─────┘  └─────┬─────┘  └──────┬──────┘ │          │
│  │        │               │               │        │          │
│  │        ▼               ▼               ▼        │          │
│  │  ┌─────────────────────────────────────────────┐│          │
│  │  │    Jev AI Engine (jev_client.py)             ││          │
│  │  │  • noul → 二元故障判定                       ││          │
│  │  │  • choice → 故障分类                         ││          │
│  │  │  • score → 严重度评分                        ││          │
│  │  │  • 语义去重 (should_skip_duplicate)           ││          │
│  │  └─────────────────────────────────────────────┘│          │
│  └─────────────────────────────────────────────────┘          │
│                          │                                     │
│           ┌──────────────┼──────────────┐                     │
│           ▼              ▼              ▼                     │
│  ┌──────────────┐ ┌────────────┐ ┌────────────────────┐      │
│  │ ResultStore  │ │ AlertMgr   │ │ Prometheus Metrics │      │
│  │ (SQLite)     │ │ (Webhook)  │ │ (.prom + /metrics) │      │
│  └──────┬───────┘ └─────┬──────┘ └────────┬───────────┘      │
│         │               │                 │                   │
│         ▼               ▼                 ▼                   │
│  ┌────────────┐  ┌───────────┐  ┌──────────────────┐         │
│  │ /health    │  │ 飞书/钉钉  │  │ Grafana Dashboard│         │
│  │ /history   │  │ 企微/Slack │  │ Prometheus Server│         │
│  │ /metrics   │  │ Webhook    │  │ Alertmanager     │         │
│  └────────────┘  └───────────┘  └──────────────────┘         │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Reports: JSON (结构化) + HTML (可视化大屏)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 五、文件清单与职责

| 文件 | 角色 | 描述 |
|:---|:---|:---|
| `main.py` | CLI 入口 | 单站点巡检命令行入口，支持全量 CLI 参数 |
| `run_inspection.py` | 多站点入口 | 多站点并发巡检编排器，支持 `--serve` 启动健康检查 |
| `crawler.py` | 巡检核心引擎 | Playwright 交互遍历 + 多维错误检测 + AI 研判 |
| `jev_client.py` | AI 决策客户端 | Jev System One API 封装（noul/choice/score） |
| `config.py` | 配置管理 | DataClass 配置模型，支持 JSON/Env 加载 |
| `alert_manager.py` | 告警通知 | 多通道 Webhook 告警（飞书/钉钉/企微/Slack） |
| `scheduler.py` | 调度与持久化 | 并发调度 + 重试退避 + SQLite 持久化 + 健康检查 HTTP |
| `generate_report.py` | HTML 报告 | 可视化巡检结果大屏 |
| `test_inspection.py` | 单元+集成测试 | 9 项测试：配置/告警/安全/指纹/端到端 |
| `test_scheduler.py` | 调度器测试 | 10 项测试：持久化/健康检查/并发/HTTP 端点 |
| `inspection_config.sample.json` | 配置模板 | 单站点巡检配置示例 |
| `sites_config.sample.json` | 多站点配置 | 多站点并发巡检配置示例 |

---

## 六、生产部署快速参考

### 6.1 单站点定时巡检 (Cron)
```bash
# 每 10 分钟巡检一次
*/10 * * * * cd /opt/inspection && python3 main.py --config inspection_config.sample.json --fail-on-error >> /var/log/inspection.log 2>&1
```

### 6.2 多站点并发巡检 + 健康检查
```bash
# 启动后常驻，暴露 /health + /metrics 端点
python3 run_inspection.py --config sites_config.sample.json --serve --port 8089
```

### 6.3 Prometheus 抓取配置
```yaml
scrape_configs:
  - job_name: 'web-inspection'
    static_configs:
      - targets: ['inspection-host:8089']
    metrics_path: '/metrics'
    scrape_interval: 60s
```

### 6.4 Docker 部署
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-noble
WORKDIR /app
COPY . .
RUN pip install playwright && playwright install chromium
ENV TYPESAFE_API_KEY=your_api_key
ENV INSPECTION_WEBHOOK_URL=https://open.feishu.cn/...
CMD ["python3", "run_inspection.py", "--config", "sites_config.sample.json", "--serve"]
```
