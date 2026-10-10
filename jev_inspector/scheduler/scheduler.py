"""
Multi-Site Inspection Scheduler & Concurrent Orchestrator.
Enterprise-grade parallel inspection runner with:
- Concurrent multi-site inspection (ThreadPool-based)
- Retry with exponential backoff per site
- Aggregated health dashboard result
- Historical result persistence (SQLite)
- Health check HTTP endpoint for uptime monitoring
"""

import os
import json
import time
import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from ..core.config import InspectionConfig, AlertConfig
from ..engine.crawler import WebInspectionCrawler
from ..alert.alert_manager import AlertManager

logger = logging.getLogger("inspection.scheduler")


@dataclass
class SiteTarget:
    """Represents a single site to inspect."""
    name: str
    url: str
    max_actions: int = 20
    auth_cookies: Optional[List[Dict[str, Any]]] = None
    alert_webhook_url: Optional[str] = None
    alert_webhook_type: str = "generic"
    tags: List[str] = field(default_factory=list)


class ResultStore:
    """SQLite-based persistent result store for inspection history."""

    def __init__(self, db_path: str = "inspection_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspection_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_name TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_actions INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    error_details TEXT,
                    run_timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_site ON inspection_runs(site_name, run_timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_status ON inspection_runs(status)
            """)

    def save_result(self, site_name: str, report: Dict[str, Any]):
        summary = report.get("summary", {})
        errors = report.get("errors_detected", [])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO inspection_runs
                   (site_name, target_url, status, total_actions, total_errors, duration_seconds, error_details, run_timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    site_name,
                    summary.get("target_url", ""),
                    summary.get("status", "UNKNOWN"),
                    summary.get("total_actions_executed", 0),
                    summary.get("total_errors_detected", 0),
                    summary.get("duration_seconds", 0),
                    json.dumps(errors, ensure_ascii=False)[:4000] if errors else None,
                    summary.get("timestamp", datetime.now(timezone.utc).isoformat())
                )
            )

    def get_latest_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM inspection_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_site_history(self, site_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM inspection_runs WHERE site_name = ? ORDER BY id DESC LIMIT ?",
                (site_name, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_health_summary(self) -> Dict[str, Any]:
        """Get aggregated health status across all monitored sites."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Latest run per site
            rows = conn.execute("""
                SELECT site_name, status, total_errors, duration_seconds, run_timestamp
                FROM inspection_runs
                WHERE id IN (
                    SELECT MAX(id) FROM inspection_runs GROUP BY site_name
                )
            """).fetchall()

            sites = []
            all_healthy = True
            for r in rows:
                entry = dict(r)
                if entry["status"] != "PASSED":
                    all_healthy = False
                sites.append(entry)

            total_runs = conn.execute("SELECT COUNT(*) FROM inspection_runs").fetchone()[0]

            return {
                "overall_status": "HEALTHY" if all_healthy else "DEGRADED",
                "total_monitored_sites": len(sites),
                "total_historical_runs": total_runs,
                "sites": sites,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }


class InspectionScheduler:
    """Concurrent multi-site inspection orchestrator."""

    def __init__(
        self,
        sites: List[SiteTarget],
        concurrency: int = 3,
        max_retries: int = 2,
        retry_backoff_base: float = 5.0,
        api_key: Optional[str] = None,
        result_store: Optional[ResultStore] = None,
        global_alert: Optional[AlertManager] = None
    ):
        self.sites = sites
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        self.result_store = result_store or ResultStore()
        self.global_alert = global_alert
        self.results: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _run_single_site(self, site: SiteTarget) -> Dict[str, Any]:
        """Run inspection on a single site with retry and backoff."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[{site.name}] Attempt {attempt}/{self.max_retries}: Inspecting {site.url}")

                cfg = InspectionConfig(
                    target_url=site.url,
                    max_actions=site.max_actions,
                    headless=True,
                    report_json_path=f"report_{site.name.lower().replace(' ', '_')}.json",
                    report_html_path=f"report_{site.name.lower().replace(' ', '_')}.html"
                )

                if site.alert_webhook_url:
                    cfg.alert.enabled = True
                    cfg.alert.webhook_url = site.alert_webhook_url
                    cfg.alert.webhook_type = site.alert_webhook_type

                if self.api_key:
                    cfg.api_key = self.api_key

                crawler = WebInspectionCrawler(config=cfg)
                report = crawler.run()

                # Persist
                self.result_store.save_result(site.name, report)

                with self._lock:
                    self.results[site.name] = report

                summary = report.get("summary", {})
                logger.info(f"[{site.name}] Completed: status={summary.get('status')}, errors={summary.get('total_errors_detected')}")
                return report

            except Exception as e:
                last_error = e
                wait_time = self.retry_backoff_base * (2 ** (attempt - 1))
                logger.error(f"[{site.name}] Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # All retries exhausted
        fail_report = {
            "summary": {
                "target_url": site.url,
                "status": "FAILED",
                "total_actions_executed": 0,
                "total_errors_detected": 1,
                "duration_seconds": 0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "errors_detected": [{
                "action": "scheduler_all_retries_exhausted",
                "detected_texts": [str(last_error)],
                "error_type": "network_error",
                "jev_confidence": 1.0,
                "severity_score": 1.0,
                "screenshot": "",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }],
            "executed_actions": [],
            "skipped_duplicates": []
        }
        self.result_store.save_result(site.name, fail_report)
        with self._lock:
            self.results[site.name] = fail_report
        return fail_report

    def run_all(self) -> Dict[str, Any]:
        """Run inspection across all configured sites concurrently."""
        start = time.time()
        logger.info(f"Starting parallel inspection for {len(self.sites)} sites (concurrency={self.concurrency})")

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {executor.submit(self._run_single_site, site): site for site in self.sites}
            for future in as_completed(futures):
                site = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"[{site.name}] Unhandled scheduler error: {e}")

        duration = round(time.time() - start, 2)

        # Build aggregated dashboard
        total_errors = 0
        site_summaries = []
        for name, report in self.results.items():
            s = report.get("summary", {})
            total_errors += s.get("total_errors_detected", 0)
            site_summaries.append({
                "name": name,
                "url": s.get("target_url"),
                "status": s.get("status"),
                "errors": s.get("total_errors_detected", 0),
                "actions": s.get("total_actions_executed", 0),
                "duration": s.get("duration_seconds", 0)
            })

        dashboard = {
            "overall_status": "FAILED" if total_errors > 0 else "PASSED",
            "total_sites": len(self.sites),
            "total_errors": total_errors,
            "total_duration_seconds": duration,
            "sites": site_summaries,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save dashboard
        with open("inspection_dashboard.json", "w", encoding="utf-8") as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)
        logger.info(f"Inspection dashboard saved to inspection_dashboard.json")

        # Global alert for any failures
        if self.global_alert and total_errors > 0:
            failed_sites = [s for s in site_summaries if s["status"] == "FAILED"]
            all_errors = []
            for name, report in self.results.items():
                all_errors.extend(report.get("errors_detected", []))
            self.global_alert.send_alert(
                title=f"巡检总览告警: {len(failed_sites)}/{len(self.sites)} 站点异常",
                summary={"target_url": "multi-site", "total_actions_executed": sum(s["actions"] for s in site_summaries), "total_errors_detected": total_errors},
                errors=all_errors[:10]
            )

        logger.info("="*60)
        logger.info(f"Multi-Site Inspection Summary: {dashboard['overall_status']}")
        for s in site_summaries:
            emoji = "✓" if s["status"] == "PASSED" else "✗"
            logger.info(f"  [{emoji}] {s['name']} ({s['url']}) → {s['status']} (errors={s['errors']}, time={s['duration']}s)")
        logger.info(f"Total Duration: {duration}s")
        logger.info("="*60)

        return dashboard


class HealthCheckServer:
    """Lightweight HTTP health check endpoint for load balancers & orchestrators.
    Responds on /health and /metrics with inspection health status.
    """

    def __init__(self, result_store: ResultStore, host: str = "0.0.0.0", port: int = 8089):
        self.result_store = result_store
        self.host = host
        self.port = port
        self._server = None
        self._thread = None

    def start(self):
        from http.server import HTTPServer, BaseHTTPRequestHandler
        store = self.result_store

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    summary = store.get_health_summary()
                    status_code = 200 if summary["overall_status"] == "HEALTHY" else 503
                    body = json.dumps(summary, ensure_ascii=False, indent=2)
                    self.send_response(status_code)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))

                elif self.path == "/metrics":
                    # Prometheus text format
                    summary = store.get_health_summary()
                    lines = [
                        "# HELP web_inspection_overall_healthy Overall inspection health (1=healthy, 0=degraded)",
                        "# TYPE web_inspection_overall_healthy gauge",
                        f'web_inspection_overall_healthy {1 if summary["overall_status"] == "HEALTHY" else 0}',
                        "# HELP web_inspection_monitored_sites Number of monitored sites",
                        "# TYPE web_inspection_monitored_sites gauge",
                        f'web_inspection_monitored_sites {summary["total_monitored_sites"]}',
                    ]
                    for site in summary.get("sites", []):
                        name = site["site_name"].replace('"', '\\"')
                        lines.append(f'web_inspection_site_status{{site="{name}"}} {1 if site["status"] == "PASSED" else 0}')
                        lines.append(f'web_inspection_site_errors{{site="{name}"}} {site.get("total_errors", 0)}')
                    body = "\n".join(lines) + "\n"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))

                elif self.path == "/history":
                    results = store.get_latest_results(100)
                    body = json.dumps(results, ensure_ascii=False, indent=2)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))

                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                logger.debug(f"HealthCheck: {format % args}")

        self._server = HTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"Health check server started at http://{self.host}:{self.port}/health")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
