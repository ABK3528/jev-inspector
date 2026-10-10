import json
import os
import glob
from datetime import datetime

def generate_html_report(json_paths, output_html="traversal_report.html"):
    reports_data = []
    total_actions = 0
    total_skipped = 0
    total_errors = 0

    for path in json_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                site_name = os.path.basename(path).replace(".json", "").replace("report_", "").upper()
                summary = data.get("summary", {})
                actions_cnt = summary.get("total_actions_executed", 0)
                skipped_cnt = summary.get("total_duplicates_skipped", 0)
                errors_cnt = summary.get("total_errors_detected", 0)
                
                total_actions += actions_cnt
                total_skipped += skipped_cnt
                total_errors += errors_cnt
                
                reports_data.append({
                    "file": path,
                    "site_name": site_name,
                    "target_url": summary.get("target_url", "未知 URL"),
                    "actions_count": actions_cnt,
                    "skipped_count": skipped_cnt,
                    "errors_count": errors_cnt,
                    "errors": data.get("errors_detected", []),
                    "actions": data.get("executed_actions", []),
                    "skipped": data.get("skipped_duplicates", [])
                })
        except Exception as e:
            print(f"Error loading {path}: {e}")

    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jev 智能 Web 巡检与遍历综合报告</title>
    <style>
        :root {{
            --primary: #3b82f6;
            --primary-bg: #eff6ff;
            --danger: #ef4444;
            --danger-bg: #fef2f2;
            --success: #10b981;
            --success-bg: #ecfdf5;
            --warning: #f59e0b;
            --warning-bg: #fffbeb;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --bg-card: #ffffff;
            --bg-body: #f8fafc;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            line-height: 1.6;
            padding: 32px 24px;
        }}
        .container {{
            max-width: 1240px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border);
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header .meta {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 6px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background: var(--bg-card);
            padding: 22px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            position: relative;
            overflow: hidden;
        }}
        .stat-card::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: #94a3b8;
        }}
        .stat-card.primary::after {{ background: var(--primary); }}
        .stat-card.danger::after {{ background: var(--danger); }}
        .stat-card.success::after {{ background: var(--success); }}
        .stat-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }}
        .stat-val {{
            font-size: 34px;
            font-weight: 800;
            margin-top: 4px;
            color: #0f172a;
        }}
        .stat-card.primary .stat-val {{ color: var(--primary); }}
        .stat-card.danger .stat-val {{ color: var(--danger); }}
        .stat-card.success .stat-val {{ color: var(--success); }}

        .card {{
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            overflow: hidden;
        }}
        .card-header {{
            padding: 18px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #ffffff;
            cursor: pointer;
            user-select: none;
        }}
        .card-header:hover {{
            background: #f8fafc;
        }}
        .site-title {{
            font-size: 17px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .badge {{
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 20px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .badge-danger {{ background: var(--danger-bg); color: var(--danger); border: 1px solid #fecaca; }}
        .badge-success {{ background: var(--success-bg); color: var(--success); border: 1px solid #a7f3d0; }}
        .badge-warning {{ background: var(--warning-bg); color: var(--warning); border: 1px solid #fde68a; }}
        .badge-primary {{ background: var(--primary-bg); color: var(--primary); border: 1px solid #bfdbfe; }}
        .badge-gray {{ background: #f1f5f9; color: var(--text-muted); border: 1px solid #e2e8f0; }}

        .card-body {{
            padding: 24px;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .error-card {{
            background: #fff1f2;
            border: 1px solid #fecdd3;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        .error-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .error-type-tag {{
            background: #be123c;
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .error-score-tag {{
            font-size: 12px;
            font-weight: 600;
            color: #9f1239;
        }}
        .error-action-desc {{
            font-size: 13px;
            font-weight: 600;
            color: #881337;
            margin-bottom: 8px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .error-text-content {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 12px;
            color: #4c0519;
            background: #ffe4e6;
            padding: 10px 14px;
            border-radius: 6px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .screenshot-preview {{
            margin-top: 10px;
            max-width: 320px;
            border-radius: 6px;
            border: 1px solid #fca5a5;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 8px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: #f8fafc;
            color: var(--text-muted);
            font-weight: 600;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:hover td {{
            background: #f8fafc;
        }}
        .mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .status-ok {{
            color: var(--success);
            font-weight: 700;
        }}
        .status-fail {{
            color: var(--danger);
            font-weight: 700;
        }}
        .skipped-box {{
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            padding: 14px 18px;
            font-size: 13px;
            color: var(--text-muted);
        }}
        .toggle-icon {{
            font-size: 12px;
            color: var(--text-muted);
            transition: transform 0.2s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>⚡ Jev 智能 Web 页面自动化巡检报告</h1>
                <div class="meta">
                    决策模型: <strong>TypeSafe System One (jev-latest)</strong> &nbsp;|&nbsp; 
                    自动化引擎: <strong>Playwright Chromium</strong> &nbsp;|&nbsp; 
                    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            <div>
                <span class="badge badge-primary">深度去重与错误分类系统已启用</span>
            </div>
        </div>

        <!-- 汇总指标卡片 -->
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="stat-label">巡检站点数</div>
                <div class="stat-val">{len(reports_data)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">已执行控件交互</div>
                <div class="stat-val">{total_actions}</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">容器去重跳过数</div>
                <div class="stat-val">{total_skipped}</div>
            </div>
            <div class="stat-card danger">
                <div class="stat-label">Jev 捕获异常总数</div>
                <div class="stat-val">{total_errors}</div>
            </div>
        </div>
"""

    for r in reports_data:
        err_badge = f'<span class="badge badge-danger">{r["errors_count"]} 项异常</span>' if r["errors_count"] > 0 else '<span class="badge badge-success">0 异常</span>'

        # 错误卡片渲染
        errors_html = ""
        if r["errors"]:
            errors_html = '<div style="margin-bottom: 24px;"><div class="section-title" style="color: var(--danger);">🚨 发现的异常与错误信息 (Jev 分类评级)</div>'
            for err in r["errors"]:
                detected_str = "\\n".join(err.get("detected_texts", []))
                screenshot_tag = ""
                sc_path = err.get("screenshot", "")
                if sc_path and os.path.exists(sc_path):
                    screenshot_tag = f'<div><a href="{sc_path}" target="_blank"><img src="{sc_path}" class="screenshot-preview" alt="Error Screenshot" /></a></div>'

                score_info = f"严重度评分: {err.get('severity_score', 0):.2f}" if 'severity_score' in err else f"置信度: {err.get('jev_confidence', 0):.2f}"
                errors_html += f"""
                <div class="error-card">
                    <div class="error-header">
                        <span class="error-type-tag">{err.get('error_type', 'error')}</span>
                        <span class="error-score-tag">{score_info}</span>
                    </div>
                    <div class="error-action-desc">操作触发: {err.get('action', '')}</div>
                    <div class="error-text-content">{detected_str}</div>
                    {screenshot_tag}
                </div>
                """
            errors_html += '</div>'
        else:
            errors_html = '<div style="margin-bottom: 20px;"><div class="section-title" style="color: var(--success);">✅ 健康状态：未发现系统/网络崩溃或异常请求</div></div>'

        # 执行动作列表渲染
        actions_html = ""
        if r["actions"]:
            actions_rows = ""
            for act in r["actions"][:15]:
                status_cls = "status-ok" if "success" in act.get("status", "") else "status-fail"
                status_txt = "成功" if "success" in act.get("status", "") else "失败"
                actions_rows += f"""
                <tr>
                    <td style="width: 50px;">#{act.get('step')}</td>
                    <td class="mono">{act.get('action')}</td>
                    <td class="{status_cls}">{status_txt}</td>
                    <td class="mono" style="color: var(--text-muted); font-size: 11px;">{act.get('signature')}</td>
                </tr>
                """
            actions_html = f"""
            <div style="margin-bottom: 24px;">
                <div class="section-title">⚡ 控件交互执行明细 (展示前 {min(len(r['actions']), 15)} 项)</div>
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>控件与操作目标</th>
                            <th>执行状态</th>
                            <th>结构指纹 / 类型分类</th>
                        </tr>
                    </thead>
                    <tbody>
                        {actions_rows}
                    </tbody>
                </table>
            </div>
            """

        # 去重机制摘要
        skipped_html = f"""
        <div>
            <div class="section-title">🛡️ 智能去重机制数据统计</div>
            <div class="skipped-box">
                在当前页面中，基于 <strong>DOM 容器模式（Table / Card / List / Grid）</strong> 与 <strong>Jev 语义判定</strong>，已自动识别并过滤了 <strong>{r['skipped_count']}</strong> 个同类型冗余元素，确保全面覆盖各类交互的同时极大降低了重复请求开销。
            </div>
        </div>
        """

        html_template += f"""
        <div class="card">
            <div class="card-header" onclick="toggleCard(this)">
                <div class="site-title">
                    <span>🌐 {r['site_name']}</span>
                    <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">({r['target_url']})</span>
                    {err_badge}
                    <span class="badge badge-gray">{r['actions_count']} 交互 / {r['skipped_count']} 过滤</span>
                </div>
                <div class="toggle-icon">▼</div>
            </div>
            <div class="card-body">
                {errors_html}
                {actions_html}
                {skipped_html}
            </div>
        </div>
        """

    html_template += """
    </div>
    <script>
        function toggleCard(header) {
            const body = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon');
            if (body.style.display === 'none') {
                body.style.display = 'block';
                icon.style.transform = 'rotate(0deg)';
            } else {
                body.style.display = 'none';
                icon.style.transform = 'rotate(-90deg)';
            }
        }
    </script>
</body>
</html>
"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"[✓] Enhanced HTML report generated: {output_html}")

if __name__ == "__main__":
    json_files = glob.glob("report_*.json") + ["github_trending.json"]
    generate_html_report(list(set(json_files)), "traversal_report.html")
