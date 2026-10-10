# 线上真实巡检引擎架构与优化实战指南 (Online Synthetic Inspection Guide)

本项目是一个基于 **Jev (TypeSafe System One 智能决策模型)** 和 **Playwright 真实浏览器环境** 的 **企业级线上 Web 自动化遍历与智能异常巡检工具**。

---

## 1. 这个爬虫是做什么的？

### 核心定位
传统爬虫主要用于“网页数据抓取（Data Scraping）”，而本项目本质上是一个 **“线上交互式主动巡检与拨测引擎（Synthetic Monitoring & Error Hunting）”**：
1. **真实无头浏览器渲染与交互**：
   - 自动识别页面内可交互控件（Button, Link, Input, Select, Menu, Tab 等）。
   - 具备安全防护机制（自动识别并规避“登出”、“删除账号”、“清空数据”等破坏性按钮）。
2. **结构与语义级智能去重**：
   - 基于 DOM 结构指纹（如表格行 `tr`、卡片网格 `card`、列表项 `li`）进行去重，避免对同类数据大量重复点击。
   - 结合 Jev AI 决策模型进行语义冗余评估，精简遍历路径。
3. **多维故障捕获与 AI 智能定级**：
   - **DOM 视窗**：页面弹窗、Toast 提醒、Alert 警告。
   - **控制台**：Console Errors / Unhandled Exceptions。
   - **网络层**：实时拦截 4xx / 5xx 故障请求。
   - **Jev AI 研判**：区分“正常业务提示（如操作成功）”与“真实故障（500、网络超时、系统开小差、400 异常等）”，给出故障类型、置信度与严重度评分。

---

## 2. 优化后的生产级巡检能力架构

为了从“实验性脚本”升级为“**线上巡检可以 100% 依赖的真实工具**”，已完成以下核心能力改造：

| 模块 | 优化前状态 | 优化后（线上可依赖） |
| :--- | :--- | :--- |
| **配置管理** | 参数分散在代码与简单 argparse 中 | 独立 `config.py`，支持 JSON 配置文件、CLI 参数与环境变量（支持容器部署） |
| **告警通知** | 仅控制台打印与本地生成文件 | 生产级 `alert_manager.py`，原生支持 **飞书(Lark)、钉钉、企业微信、Slack、通用 Webhook** |
| **指标监控** | 无 Metrics 输出 | 自动生成 **Prometheus / OpenMetrics** 格式指标文件（`inspection_metrics.prom`） |
| **巡检退出码** | 总是 exit 0，CI/CD 无法感知失败 | 巡检发现异常自动返回 **Exit Code 1**，无异常返回 **0**，完美对接 Jenkins/GitLab CI/Cron |
| **安全防护** | 硬编码正则 | 可配置安全黑名单，严格防护破坏性点击与跨域跳出 |
| **测试与验证** | 缺少单元与回归测试 | 9 项全覆盖自动化测试（`test_inspection.py`），包含 Mock Web 模拟端到端闭环 |

---

## 3. 快速上手

### 3.1 运行单次巡检（使用默认配置）
```bash
python3 main.py --url https://the-internet.herokuapp.com/status_codes --max-actions 20
```

### 3.2 使用生产配置文件与飞书/钉钉告警
```bash
python3 main.py --config inspection_config.sample.json \
  --webhook-url https://open.feishu.cn/open-apis/bot/v2/hook/xxx \
  --webhook-type feishu
```

### 3.3 CI/CD 与 定时任务 (Cron) 巡检示例
在 Cron 或 CI/CD 流水线中，依赖退出码直接判断服务健康状况：
```bash
# 每天凌晨或每 10 分钟运行一次
python3 main.py --config inspection_config.sample.json --fail-on-error

# 检查结果
if [ $? -eq 0 ]; then
  echo "巡检通过：线上服务各项组件与交互正常"
else
  echo "巡检失败：发现线上服务异常，已触发告警通道并保存截图"
fi
```

### 3.4 单元测试执行
```bash
python3 -m unittest test_inspection.py
```

---

## 4. 产出交付物说明

每次巡检运行完成后，系统会自动生成：
1. **JSON 结构化报告**（默认 `traversal_report.json`）：供日志平台采集或下游系统分析。
2. **HTML 可视化交互大屏**（默认 `traversal_report.html`）：支持按站点、错误类型、严重度筛选，查看异常截图与上下文。
3. **Prometheus 监控指标**（默认 `inspection_metrics.prom`）：提供 `web_inspection_status`、`web_inspection_errors_total` 等指标供 Node Exporter / Prometheus 抓取。
4. **实时告警推送**：有故障时秒级推送至飞书/钉钉/企业微信群。
