# Jev-Inspector: Enterprise AI-Powered Web Synthetic Monitoring & Error Hunting Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Playwright-Chromium-green?logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/AI_Engine-TypeSafe_Jev_System_One-purple" alt="TypeSafe Jev">
  <img src="https://img.shields.io/badge/Tests-45_Passing-brightgreen?logo=pytest&logoColor=white" alt="Tests">
  <img src="https://img.shields.io/badge/Architecture-Modular_Package-orange" alt="Architecture">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License">
</p>

> **Jev-Inspector** 是一套专为生产环境打造的**工业级全自主 Web 线上巡检与故障捕获平台**。  
> 告别手写高脆性 E2E 脚本的沉重负担，系统基于**自适应真实浏览器驱动**与 **TypeSafe Jev 认知决策模型**，实现整站多层级链路遍历、四层智能去重、三级弹性回溯防御与多维（DOM/Console/Network）异常捕获。

---

## 📌 为什么需要 Jev-Inspector？传统巡检的痛点

线上巡检（Synthetic Monitoring / 拨测）是保障高可用架构（SRE）不可或缺的防线。然而，无论是编写 **Playwright / Cypress** 脚本，还是采购 **Datadog Synthetics / Checkly** 等 SaaS 产品，在复杂生产场景中均面临三大死局：

1. **写不完、维护不起的脚本**：企业级 Admin 后台、CRM、复杂 SaaS 动辄包含上千个表单与菜单。为每个按钮手写 E2E 脚本成本极高，前端 UI 一旦迭代重构，测试脚本大面积雪崩失效。
2. **抓不住的 SPA 前端“静默崩溃”**：现代单页应用在后端接口 500、网络超时或前端抛出未捕获 Promise Rejection 时，页面往往不会跳 404，而是弹出一个闪烁即逝的 Toast（如“系统开小差”）。传统的 HTTP 状态码探活完全无法感知此类严重业务故障。
3. **陷入无限下钻与标签页内存泄漏**：自主爬虫遇到带有 `target="_blank"` 的外部链接或海量商品详情页时，容易导致浏览器 Tab 堆积耗尽内存，或陷在死循环中耗尽算力。

**Jev-Inspector** 彻底解决了上述问题：**输入根 URL，即刻开启兼具“广度全站自主探索”与“深度核心链路断言”的现代化全景巡检**。

---

## 🎯 典型使用场景 (Use Cases)

### 场景 1：大型中后台/SaaS 系统无人值守巡检 (Zero-Script Autonomous Inspection)
- **适用对象**：内部 ERP、CRM、OA 协同、多租户管理后台。
- **痛点**：功能模块数以百计，QA 团队无法为每个页面维护自动化用例。
- **解决方案**：配置根 URL 与鉴权信息，引擎利用 **BFS 递归遍历整站**，结合 **Path Archetyping（路径模板聚类）** 与 **DOM 结构指纹去重**，在极低资源开销下完成全站页面与控件原型的 100% 遍历，实时拦截控制台报错与接口 5xx。

### 场景 2：核心商业交易链路 7x24 拨测与 SLA 监控 (Critical Journey Monitoring)
- **适用对象**：电商结算、开户审批、在线支付、SaaS 用户签约主流程。
- **痛点**：简单的 HTTP 接口探活无法验证真实前端组件的渲染状态与交互时延。
- **解决方案**：使用 `flow_engine` 声明确定性业务链路（如：登录 → 搜索商品 → 加入购物车 → 跳转新标签页审批）。配置严格的 **SLA 时延红线** 与 **多属性断言**，一旦出现功能损坏或时延违约，秒级推送故障现场截图与报错堆栈。

### 场景 3：发布上线即时冒烟与 CI/CD 质量门禁 (Deployment Verification & Gate)
- **适用对象**：微前端集群、频繁灰度发布的生产系统。
- **痛点**：发版后依赖人工点点点，灰度阶段无法快速扫描隐藏的前端资源加载失效。
- **解决方案**：将 Jev-Inspector 嵌入 Jenkins / GitHub Actions / GitLab CI。构建部署后自动触发执行，利用 `--fail-on-error` 参数控制流程，1 分钟内完成整站健康扫描，阻断缺陷扩散。

### 场景 4：多分支/多租户站点集群的并发巡检 (Multi-Site Concurrent Fleet)
- **适用对象**：为数百家企业客户部署了私有子域名的 SaaS 服务商。
- **痛点**：每个租户配置不同，需要统一纳管、并发巡检与统一监控上报。
- **解决方案**：利用 `InspectionScheduler` 统一编排多站点目标池，开启线程池隔离并发探测，历史结果自动入库 SQLite，并对外提供标准 Prometheus `/metrics` 指标供企业级 Grafana 统一看板纳管。

---

## 🚀 核心架构与创新机制

```
jev_inspector/                      # 现代化工程分层核心包
├── core/                           # 配置模型与环境变量覆盖驱动
│   ├── config.py                   # InspectionConfig, AuthConfig, AlertConfig
├── engine/                         # 双模执行核心
│   ├── crawler.py                  # BFS整站拓扑探索, 四层去重, 三级弹性回溯, 覆盖率统计
│   ├── flow_engine.py              # FlowExecutor, 显式多页面切换, SLA校验, 断言引擎
├── decision/                       # AI 与启发式研判决策
│   ├── jev_client.py               # TypeSafe Jev System One Client (noul/choice/score)
├── alert/                          # 企业级协同告警
│   ├── alert_manager.py            # 飞书卡片 / 钉钉 Markdown / 企业微信 / Slack / Webhook
├── scheduler/                      # 高可用并发调度与云原生暴露
│   ├── scheduler.py                # InspectionScheduler, ResultStore, HealthCheckServer
├── reporting/                      # 可视化报表渲染
│   ├── generate_report.py          # 交互式单页 HTML Dashboard 生成器
└── extensions/                     # 🔌 插件扩展机制 (生命周期钩子系统)
    ├── base.py                     # BaseExtension, ExtensionManager (留出扩展口子)
```

### 1. 四层递进式去重机制 (4-Level Progressive Deduplication)
- **L1 URL 规范化**：自动剔除 `utm_*`、时间戳、会话噪点并重排 Query 参数，避免同质 URL 反复排队；
- **L2 Path Archetyping（路径模板聚类）**：自动将 `/items/1001`、`/items/1002` 归纳为模版原型 `/items/:id`，并施加采样配额上限（`max_pages_per_pattern`），阻断无限翻页与商品列表陷阱；
- **L3 DOM 结构指纹 (Structural Fingerprinting)**：自动识别列表项（`li`）、表格行（`tr`）、卡片网格（`card`），归纳同构控件容器，对重复项执行跳过；
- **L4 Jev AI 语义去重**：调用 Jev 认知决策模型，秒级识别语义同构的冗余控件。

### 2. 三级弹性回溯防御 (Elastic 3-Level Backtracking)
解决了无状态爬虫在真实有状态浏览器中无法回溯的难题：
- **L1 级原位软回溯**：交互弹出 Modal 或 Drawer 后，自动触发 ESC 并点击关闭按钮，恢复底层页面可交互性；
- **L2 级浏览器历史回溯**：检测到页面发生外部路由漂移，自动调用带超时熔断的 `page.go_back()` 安全回退；
- **L3 级硬重置与上下文复原**：若页面被不可逆破坏或回退失败，强制重新加载目标 URL，恢复干净会话上下文。

### 3. Multi-Tab Guardian（多标签页自动守护者）
在 BrowserContext 层级监听所有弹出的 Popup 和 `target="_blank"` 新标签页，自动进行网络与控制台验活，完成后安全自动关闭，保证内存恒定、避免焦点迷失。

### 4. 科学的双重覆盖率度量体系 (Dual Coverage Metrics)
- **🎯 控件原型功能覆盖率 (`functional_archetype_coverage_rate`)**：$\frac{\text{已测试的独立控件指纹数}}{\text{整站发现的全部独立控件原型总数}} \times 100\%$，真实反映整站不同交互原型的测试广度；
- **💡 原生元素去重采样比 (`raw_sampling_rate`)**：$\frac{\text{交互执行数}}{\text{遭遇候选DOM总量}} \times 100\%$，精准度量去重引擎过滤冗余开销的能力（实测可过滤 95%+ 冗余点击）；
- **🌐 站点拓扑构建**：输出全站页面列表与跳转有向依赖边，生成全局站点拓扑图。

---

## 🛠️ 快速上手与操作指南

### 1. 环境准备
```bash
git clone https://github.com/ABK3528/jev-inspector.git
cd jev-inspector

# 安装依赖并安装 Chromium 浏览器内核
pip install playwright
playwright install chromium
```

*(可选) 配置 TypeSafe Jev 模型 API Key（若未配置，系统会自动切换为本地规则库，核心巡检功能完全可用）：*
```bash
export TYPESAFE_API_KEY=""
```

---

### 2. 命令行 CLI 快速使用

#### 启动整站递归智能巡检 (Whole-Site BFS Traversal)
```bash
# 从入口 URL 开始，自动发现整站内部链接，下钻 2 层，最大巡检 10 个页面
python3 main.py --url https://httpbin.org/forms/post --crawl-mode site --max-pages 10 --max-depth 2
```

#### 仅巡检指定单个页面 (Single Page Mode)
```bash
python3 main.py --url https://httpbin.org/forms/post --crawl-mode page --max-actions 20
```

#### 运行真实公网站点端到端 Demo (含全景覆盖率报表)
```bash
# Demo 1: Hacker News 全站多层级巡检 (实测 8 个核心功能页, 1000+ 条拓扑边, 100% 控件原型覆盖)
python3 demo_real_website.py

# Demo 2: Quotes to Scrape 受保护登录后台巡检 (自动登录, 维持会话, 阻断 Logout, 100% 控件原型覆盖)
python3 demo_authenticated_inspection.py
```

#### 结合生产配置文件并配置飞书/钉钉告警
```bash
python3 main.py --config inspection_config.sample.json \
  --webhook-url "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx" \
  --webhook-type feishu
```

---

### 3. 作为 Python SDK 在工程中集成

现代化的分层包结构支持一行代码轻松引入：

```python
from jev_inspector import WebInspectionCrawler, InspectionConfig, AuthConfig

# 1. 声明整站巡检配置
config = InspectionConfig(
    target_url="https://example.com/admin",
    crawl_mode="site",
    max_pages=15,
    max_depth=3,
    max_pages_per_pattern=2,  # 模板聚类采样上限，阻断无限分页
    # 自动登录受保护区域
    auth=AuthConfig(
        enabled=True,
        login_url="https://example.com/login",
        username_selector="#user",
        password_selector="#pwd",
        submit_selector="#submit-btn",
        username="admin_test",
        password="SafePassword123"
    ),
    # 安全关键词过滤：杜绝误触登出或删除
    destructive_keywords=["logout", "delete", "注销", "清空"]
)

# 2. 启动巡检
crawler = WebInspectionCrawler(config=config)
report = crawler.run()

# 3. 读取双重覆盖率指标
coverage = report["summary"]["coverage_metrics"]
print(f"控件原型功能覆盖率: {coverage['functional_archetype_coverage_rate'] * 100:.2f}%")
print(f"整站发现核心页面数: {coverage['pages_discovered_count']}")
```

---

### 4. 显式多页面切换与业务链路编排 (Flow Engine)

针对具有严格顺序的业务链条，支持通过 `FlowDefinition` 实现显式多页面/多标签页精准切换：

```python
from jev_inspector import FlowDefinition, FlowStep, FlowExecutor

flow = FlowDefinition(
    name="电商多标签页下单校验",
    start_url="https://mall.example.com",
    sla_max_duration_seconds=15.0,  # SLA 时延红线
    steps=[
        # 1. 点击商品链接并精确切换至新开的子标签页
        FlowStep(action="click_and_expect_page", selector="a.item-link", value="detail_tab"),
        
        # 2. 在子标签页中执行断言
        FlowStep(action="assert", selector="#item-price", assert_type="visible"),
        FlowStep(action="assert", assert_type="title_matches", expected=r"商品详情"),
        
        # 3. 关闭子标签页，焦点自动安全回退至主页面
        FlowStep(action="close_tab", value="detail_tab"),
        
        # 4. 验证主页面会话状态
        FlowStep(action="assert", selector="#cart-count", assert_type="text_contains", expected="1")
    ]
)
```

---

### 5. 🔌 扩展口子：编写自定义插件 (Extensions & Hooks)

系统内置了标准生命周期钩子体系，开发者可零侵入实现自定义业务增强：

```python
from jev_inspector.extensions import BaseExtension
from playwright.sync_api import Page
from typing import Dict, Any

class SecurityAuditExtension(BaseExtension):
    """自定义安全合规与实时故障转发插件"""

    def on_page_loaded(self, page: Page, url: str) -> None:
        # 在每个页面加载完毕后，检查是否包含未授权的外部脚本注入
        print(f"[Audit] Inspecting page scripts on {url}")

    def on_before_action(self, page: Page, element_info: Dict[str, Any]) -> bool:
        # 前置守卫：动态拦截包含 'pay_test' 的敏感提交按钮
        if "pay_test" in element_info.get("id", ""):
            print("[Audit] Skipping restricted payment button.")
            return False  # 返回 False 取消该操作
        return True

    def on_error_detected(self, error_record: Dict[str, Any]) -> None:
        # 即时上报 Sentry 或自动在 Jira 创建故障工单
        print(f"[Audit Alert] Dispatching error to Sentry: {error_record['action']}")

# 注册插件至巡检引擎
crawler = WebInspectionCrawler(config=config)
crawler.extensions.register(SecurityAuditExtension())
crawler.run()
```

---

### 6. 多站点集群调度与云原生探针服务

在生产环境中，可通过 `run_inspection.py` 常驻运行多站点编排与 HTTP 服务：

```bash
# 启动常驻巡检服务，在 8089 端口暴露探针
python3 run_inspection.py --config sites_config.sample.json --serve --port 8089
```

服务就绪后，企业监控平台可直接集成标准接口：
- **存活探针**：`curl http://localhost:8089/health`（返回 200/503 聚合健康状态，可直连 K8s Liveness/Readiness Probe）
- **Prometheus 指标**：`curl http://localhost:8089/metrics`（自动暴露巡检耗时、动作量、**`web_inspection_element_coverage` 控件覆盖率**、错误数）
- **巡检历史查询**：`curl http://localhost:8089/history`

---

## 📊 真实网站实测效果与覆盖率表现

基于两个典型场景的实机跑测结果如下：

| 指标维度 | Demo 1: Hacker News 全站多层级巡检 | Demo 2: Quotes to Scrape 登录保护区巡检 |
| :--- | :--- | :--- |
| **测试场景特点** | 海量文章、列表密度极高、外部跳出链接多 | 表单登录鉴权、会话保持、管理区标签页 |
| **巡检最终状态** | **`PASSED` (0 缺陷, 0 崩溃)** | **`PASSED` (0 缺陷, 0 崩溃)** |
| **页面覆盖发现** | **`8` 个核心功能页**（首页/news/newest/ask/jobs等） | **`6` 个受保护页面**（用户后台/作者详情/归档等） |
| **URL 模式原型** | 聚合提炼出 **8 类模板原型**（有效规避无限深钻） | 聚合提炼出 **6 类模板原型** |
| **站点拓扑建立** | 建立 **1,067 条有向依赖边** | 建立 **150 条有向依赖边** |
| **遭遇候选控件总量** | **2,128 个原生 DOM 元素** | **364 个原生 DOM 元素** |
| **去重机制过滤量** | **2,104 个同质元素（过滤率 98.87%）** | **353 个同质元素（过滤率 96.98%）** |
| **🎯 控件原型功能覆盖率** | **`100.00%` (24/24 种功能指纹全部测试)** | **`100.00%` (11/11 种功能指纹全部测试)** |
| **💡 原生元素去重采样比** | **`1.13%` (极低消耗覆盖所有原型)** | **`3.02%` (极低消耗覆盖所有原型)** |
| **安全沙箱机制** | L2 回退成功触发 16 次（跳出外链秒级回退） | 拦截 Logout 按钮 7 次（登录态完好无损） |
| **整站巡检总耗时** | **44.76s** | **30.27s** |

---

## 📈 与行业竞品全方位横向对比

| 评估维度 | Datadog Synthetics | Checkly | Grafana k6 Browser | Sentry | **Jev-Inspector (本项目)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **交互与探测方式** | 需人工手写/录制脚本 | 需手写 Playwright 脚本 | 需手写 k6 脚本 | 被动 SDK 埋点 | **零脚本 AI 全自主遍历 + 四层去重** |
| **无限深度陷阱防御** | ❌ 无 (易死循环) | ❌ 无 (易脚本超时) | ❌ 无 | N/A | **✅ Path Archetyping 路径模板聚类** |
| **AI 智能决策研判** | ❌ 无 | ❌ 无 | ❌ 无 | 仅支持错误聚合 | **✅ Jev 原语研判 (二元确定+归类+评分)** |
| **故障捕获维度** | 依赖手写断言 | 依赖手写断言 | 依赖手写断言 | 仅运行时捕获 | **DOM 弹窗 + 控制台日志 + 接口 4xx/5xx 三重证据链** |
| **多页面与新 Tab 控制** | 手动配置 | 手动编写上下文 | 手工编写 | N/A | **✅ Context 级 Multi-Tab 自动守护 + 显式多流** |
| **三级状态弹性回溯** | ❌ 崩溃后直接失败 | ❌ 脚本直接抛异常 | ❌ 脚本直接抛异常 | N/A | **✅ ESC原位软回溯 + go_back + URL硬重置** |
| **覆盖率多维量化** | ❌ 仅有单次通过率 | ❌ 仅有步骤通过率 | ❌ 无 | N/A | **✅ 控件原型功能覆盖率 + 拓扑边关系映射** |
| **私有化与合规** | ❌ 仅 SaaS 托管 | ❌ 依赖云端调度 | ⚠️ 部分自建复杂 | ⚠️ 自建门槛高 | **✅ 100% 纯 Python 自托管，数据零出域** |

---

## 🧪 自动化测试套件

项目拥有高度完备的自动化测试体系，包含本地真实 HTTP 模拟服务与多标签页环境闭环：

```bash
python3 -m unittest discover -p "test_*.py"
```

```text
Ran 45 tests in 70.24s
OK
```

- **`test_advanced_crawl.py`**：L1 URL规范化、L2 Path Archetyping 模板聚类、三级弹性回溯防御与双覆盖率指标；
- **`test_site_crawl.py`**：整站 BFS 递归遍历、最大深度/页面数配额、站点拓扑构建与正则过滤；
- **`test_multitab.py`**：Multi-Tab Guardian 自动验活关闭、显式多标签页切换与断言；
- **`test_extensions.py`**：插件生命周期钩子体系（注册、前置动作拦截、异常调度）；
- **`test_flow.py`**：业务流执行引擎、规则断言及 SLA 时延违约测试；
- **`test_scheduler.py`**：并发调度器、SQLite 结果持久化、`/health`、`/metrics` HTTP 服务测试；
- **`test_inspection.py`**：配置覆盖、安全防误触过滤、结构去重及本地 Mock 端到端闭环。

---

## 📄 开源许可证

本项目采用 [Apache-2.0](LICENSE) 许可证开源。欢迎提交 Issue 与 Pull Request！
