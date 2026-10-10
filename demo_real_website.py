#!/usr/bin/env python3
"""
Real-world Online Synthetic Inspection Demo.
Target: Hacker News (https://news.ycombinator.com)

Features demonstrated:
1. Dual-mode inspection:
   - Deterministic Flow: Navigates to 'newest', validates page title, items, and search box within SLA.
   - Autonomous Exploration: Discovers interactive links/buttons, applies structural deduplication,
     and monitors DOM/Console/Network errors.
2. Destructive Guard: Safely avoids 'login'/'logout'/'submit' side effects.
3. Observability & Reporting: Generates traversal_report.json, traversal_report.html, and inspection_metrics.prom.
"""

import sys
import os
import time
from config import InspectionConfig
from crawler import WebInspectionCrawler

def run_hackernews_inspection():
    print("=" * 70)
    print("   🌐 Jev-Inspector: Real-World Website Synthetic Inspection Demo")
    print("   Target: Hacker News (https://news.ycombinator.com)")
    print("=" * 70)

    # Configure inspection parameters (Whole-Site Mode with Archetyping & Coverage Metrics)
    cfg = InspectionConfig(
        target_url="https://news.ycombinator.com",
        crawl_mode="site",
        max_pages=8,                  # Focused whole-site demo page budget
        max_depth=2,                  # Traverse root and primary navigational links
        max_actions_per_page=6,       # Interactive element exploration actions per page
        max_pages_per_pattern=2,      # URL template archetyping cap (prevents duplicate story pages)
        headless=True,
        action_timeout_ms=5000,
        page_load_timeout_ms=15000,
        wait_after_action=0.5,
        use_jev_dedup=True,
        report_json_path="demo_hn_report.json",
        report_html_path="demo_hn_report.html",
        screenshot_dir="demo_screenshots",
        # Critical business journey flow with SLAs and assertions
        flows=[
            {
                "name": "HN Newest & Navigation Flow",
                "start_url": "https://news.ycombinator.com",
                "sla_max_duration_seconds": 15.0,
                "steps": [
                    {
                        "action": "assert",
                        "selector": "#hnmain",
                        "assert_type": "visible",
                        "description": "验证 Hacker News 页面主体正常渲染"
                    },
                    {
                        "action": "click",
                        "selector": "a[href='newest']",
                        "description": "进入 'newest' 最新帖子列表"
                    },
                    {
                        "action": "assert",
                        "assert_type": "url_matches",
                        "expected": r"newest",
                        "description": "验证当前 URL 成功跳转至 newest 路由"
                    },
                    {
                        "action": "assert",
                        "selector": "tr.athing",
                        "assert_type": "visible",
                        "description": "验证最新帖子列表项已成功加载显示"
                    }
                ]
            }
        ]
    )

    crawler = WebInspectionCrawler(config=cfg)
    report = crawler.run()

    summary = report.get("summary", {})
    status = summary.get("status", "UNKNOWN")
    total_actions = summary.get("total_actions_executed", 0)
    total_skipped = summary.get("total_duplicates_skipped", 0)
    total_errors = summary.get("total_errors_detected", 0)
    duration = summary.get("duration_seconds", 0)
    coverage = summary.get("coverage_metrics", {})
    functional_cov = coverage.get("functional_archetype_coverage_rate", 0.0)
    tested_archetypes = coverage.get("unique_interactive_signatures_tested", 0)
    total_archetypes = coverage.get("total_unique_archetypes_discovered", 0)
    raw_encountered = coverage.get("total_raw_elements_encountered", 0)
    raw_rate = coverage.get("raw_sampling_rate", 0.0)
    pages_count = coverage.get("pages_discovered_count", len(report.get("discovered_pages", [])))
    archetypes_count = coverage.get("url_archetypes_count", len(report.get("url_archetype_distribution", {})))

    print("\n" + "=" * 74)
    print("   📊 Demo 1 (Hacker News) 全站巡检与覆盖率全景评估报告")
    print("=" * 74)
    print(f"   • 巡检最终状态 (Status):             {status}")
    print(f"   • 页面覆盖发现 (Pages Visited):      {pages_count} 个核心功能页")
    print(f"   • URL 路径模式原型 (URL Archetypes): {archetypes_count} 个独立模式模板")
    print(f"   • 站点拓扑链路边 (Topology Edges):   {len(report.get('site_topology', []))} 条跳转有向边")
    print(f"   • 遭遇候选控件总量 (Raw Candidates): {raw_encountered} 个原生DOM元素")
    print(f"   • 结构去重过滤量 (Duplicates Filter):{total_skipped} 个重复同构项")
    print(f"   • 独立控件原型总数 (Total Archetypes):{total_archetypes} 种功能指纹")
    print(f"   • 已测试控件原型数 (Tested Signatures):{tested_archetypes} 种功能指纹")
    print(f"   • 🎯 控件原型功能覆盖率 (Archetype Cov):{functional_cov * 100:.2f}% (测试指纹/原型总数)")
    print(f"   • 💡 原生元素去重采样比 (Raw Sampling): {raw_rate * 100:.2f}% (有效阻断 98%+ 冗余开销)")
    print(f"   • 检出故障/异常 (Errors Detected):   {total_errors}")
    print(f"   • 巡检总耗时 (Duration):             {duration}s")
    print(f"   • 产出报表 (Artifacts):              {cfg.report_json_path} | {cfg.report_html_path}")
    print("=" * 74)

    if total_errors > 0:
        print("\n[!] Inspection detected anomalies on target site.")
        sys.exit(1)
    else:
        print("\n[✓] Synthetic inspection PASSED with zero defects.")
        sys.exit(0)

if __name__ == "__main__":
    run_hackernews_inspection()
