#!/usr/bin/env python3
"""
Production Multi-Site Inspection Runner.
CLI tool to run inspection across multiple configured sites
with concurrency, retry, alerting, and health check server.

Usage:
  python3 run_inspection.py --config sites_config.json
  python3 run_inspection.py --config sites_config.json --serve --port 8089
  python3 run_inspection.py --health  # query running health check
"""

import sys
import json
import argparse
import logging

from scheduler import InspectionScheduler, SiteTarget, ResultStore, HealthCheckServer
from alert_manager import AlertManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("inspection.runner")

DEFAULT_SITES_CONFIG = [
    {
        "name": "HackerNews",
        "url": "https://news.ycombinator.com/",
        "max_actions": 10,
        "tags": ["tech", "news"]
    },
    {
        "name": "HTTPBin_Forms",
        "url": "https://httpbin.org/forms/post",
        "max_actions": 8,
        "tags": ["api", "test"]
    }
]


def load_sites(config_path: str = None) -> list:
    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sites_data = data if isinstance(data, list) else data.get("sites", [])
    else:
        sites_data = DEFAULT_SITES_CONFIG

    sites = []
    for s in sites_data:
        sites.append(SiteTarget(
            name=s["name"],
            url=s["url"],
            max_actions=s.get("max_actions", 15),
            auth_cookies=s.get("auth_cookies"),
            alert_webhook_url=s.get("alert_webhook_url"),
            alert_webhook_type=s.get("alert_webhook_type", "generic"),
            tags=s.get("tags", [])
        ))
    return sites


def main():
    parser = argparse.ArgumentParser(description="Multi-Site Web Inspection Orchestrator")
    parser.add_argument("--config", type=str, default=None, help="Path to sites config JSON file")
    parser.add_argument("--concurrency", type=int, default=3, help="Max parallel inspections")
    parser.add_argument("--retries", type=int, default=2, help="Max retry attempts per site")
    parser.add_argument("--serve", action="store_true", help="Start health check HTTP server after inspection")
    parser.add_argument("--port", type=int, default=8089, help="Health check server port")
    parser.add_argument("--health", action="store_true", help="Query health check from existing result store")
    parser.add_argument("--webhook-url", type=str, default=None, help="Global alert webhook URL")
    parser.add_argument("--webhook-type", type=str, default="generic", help="Global alert webhook type")
    parser.add_argument("--fail-on-error", action="store_true", default=True, help="Exit 1 if any site has errors")
    parser.add_argument("--no-fail-on-error", dest="fail_on_error", action="store_false")

    args = parser.parse_args()

    store = ResultStore()

    # Health check query mode
    if args.health:
        summary = store.get_health_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.exit(0 if summary["overall_status"] == "HEALTHY" else 1)

    # Load sites
    sites = load_sites(args.config)
    if not sites:
        logger.error("No sites configured. Provide --config or use defaults.")
        sys.exit(1)

    # Global alert
    global_alert = None
    if args.webhook_url:
        global_alert = AlertManager(webhook_url=args.webhook_url, webhook_type=args.webhook_type)

    print("=" * 65)
    print("   🛡️  Multi-Site Web Inspection Orchestrator")
    print("=" * 65)
    for s in sites:
        print(f"   • {s.name}: {s.url} (max_actions={s.max_actions})")
    print(f"   Concurrency: {args.concurrency} | Retries: {args.retries}")
    print("-" * 65)

    scheduler = InspectionScheduler(
        sites=sites,
        concurrency=args.concurrency,
        max_retries=args.retries,
        result_store=store,
        global_alert=global_alert
    )

    dashboard = scheduler.run_all()

    # Health check server
    if args.serve:
        health_server = HealthCheckServer(store, port=args.port)
        health_server.start()
        print(f"\n[Health Check Server] Running at http://0.0.0.0:{args.port}/health")
        print("[Health Check Server] Endpoints: /health  /metrics  /history")
        print("[Health Check Server] Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            health_server.stop()
            print("\nHealth check server stopped.")

    total_errors = dashboard.get("total_errors", 0)
    if args.fail_on_error and total_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
