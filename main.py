#!/usr/bin/env python3
"""
CLI entry point for Enterprise Web Inspection Engine.
Provides production-grade flags, configuration loading, CI exit codes, and health inspection.
"""

import sys
import argparse
import os
from jev_client import JevClient
from crawler import WebInspectionCrawler
from config import InspectionConfig, AuthConfig, AlertConfig

def parse_args():
    parser = argparse.ArgumentParser(
        description="Enterprise Web Inspection & Synthetic Monitoring Engine powered by Jev Model"
    )
    parser.add_argument("--config", type=str, default=None, help="Path to inspection JSON configuration file")
    parser.add_argument("--url", type=str, default=None, help="Target URL to inspect (overrides config)")
    parser.add_argument("--crawl-mode", type=str, choices=["site", "page"], default=None, help="Traversal mode: 'site' (whole site) or 'page' (single page)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max distinct pages to traverse in site mode")
    parser.add_argument("--max-depth", type=int, default=None, help="Max link traversal depth in site mode")
    parser.add_argument("--api-key", type=str, default=None, help="Jev/TypeSafe API Key (or TYPESAFE_API_KEY env)")
    parser.add_argument("--max-actions", type=int, default=None, help="Maximum traversal actions (e.g. 20)")
    parser.add_argument("--headless", action="store_true", default=None, help="Run browser headless (default: True)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run with browser GUI visible")
    parser.add_argument("--report", type=str, default=None, help="Path to save JSON report")
    parser.add_argument("--html-report", type=str, default=None, help="Path to save HTML dashboard report")
    parser.add_argument("--webhook-url", type=str, default=None, help="Webhook URL for alert notifications")
    parser.add_argument("--webhook-type", type=str, default=None, choices=["generic", "feishu", "dingtalk", "wecom", "slack"], help="Webhook payload format")
    parser.add_argument("--fail-on-error", action="store_true", default=True, help="Exit with code 1 if errors are detected (ideal for CI/CD / Cron monitoring)")
    parser.add_argument("--no-fail-on-error", dest="fail_on_error", action="store_false", help="Always exit with code 0 even if errors found")
    return parser.parse_args()

def main():
    args = parse_args()

    # 1. Load config from file if provided, otherwise default
    if args.config:
        cfg = InspectionConfig.from_file(args.config)
    else:
        cfg = InspectionConfig()

    # 2. CLI arguments override config
    if args.url:
        cfg.target_url = args.url
    if args.crawl_mode:
        cfg.crawl_mode = args.crawl_mode
    if args.max_pages is not None:
        cfg.max_pages = args.max_pages
    if args.max_depth is not None:
        cfg.max_depth = args.max_depth
    if args.api_key:
        cfg.api_key = args.api_key
    if args.max_actions is not None:
        cfg.max_actions = args.max_actions
    if args.headless is not None:
        cfg.headless = args.headless
    if args.report:
        cfg.report_json_path = args.report
    if args.html_report:
        cfg.report_html_path = args.html_report
    if args.webhook_url:
        cfg.alert.enabled = True
        cfg.alert.webhook_url = args.webhook_url
    if args.webhook_type:
        cfg.alert.webhook_type = args.webhook_type

    print("==================================================================")
    print("      🚀 Enterprise Web Synthetic Inspection Engine (Jev)         ")
    print("==================================================================")
    print(f"Target URL:        {cfg.target_url}")
    print(f"Max Actions:       {cfg.max_actions}")
    print(f"Headless Mode:     {cfg.headless}")
    print(f"JSON Report:       {cfg.report_json_path}")
    print(f"HTML Report:       {cfg.report_html_path}")
    print(f"Alert Webhook:     {'Configured (' + cfg.alert.webhook_type + ')' if cfg.alert.enabled else 'Disabled'}")
    print("------------------------------------------------------------------")

    crawler = WebInspectionCrawler(config=cfg)
    report = crawler.run()

    summary = report.get("summary", {})
    status = summary.get("status", "UNKNOWN")
    total_errors = summary.get("total_errors_detected", 0)

    print("\n------------------------------------------------------------------")
    print(f"Inspection Result: {status} (Errors Detected: {total_errors})")
    print("------------------------------------------------------------------")

    if args.fail_on_error and total_errors > 0:
        print("[!] Exiting with code 1 (Synthetic inspection failed with detected issues)")
        sys.exit(1)
    
    print("[✓] Inspection completed successfully. Exit code 0.")
    sys.exit(0)

if __name__ == "__main__":
    main()
