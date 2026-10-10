"""
Online Web Synthetic Inspection Engine.
Enhanced enterprise-grade crawler and health inspection tool.
Features:
- Config-driven (InspectionConfig) with CLI & environment variable overrides
- Dual-channel error detection: DOM Toasts/Alerts + Console logs + Network 4xx/5xx responses
- Playwright-based robust interaction with scroll-into-view, timeout controls and safe navigation recovery
- Destructive Action Guard: Safely avoids dangerous buttons (delete, format, drop table, logout)
- Deduplication: Structural fingerprinting + Jev System One semantic dedup
- Multi-channel notification & alerting (Feishu, DingTalk, WeCom, Slack, Generic Webhook)
- Prometheus / OpenMetrics metric output for observability
- Clean exit code semantics for CI/CD / Cron monitoring (0 = healthy, 1 = error/unhealthy)
"""

import time
import json
import re
import os
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Page, Response, BrowserContext

from jev_client import JevClient
from config import InspectionConfig
from alert_manager import AlertManager
from flow_engine import FlowDefinition, FlowExecutor

logger = logging.getLogger("inspection.engine")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)

class WebInspectionCrawler:
    def __init__(
        self,
        config: Optional[InspectionConfig] = None,
        jev_client: Optional[JevClient] = None
    ):
        self.config = config or InspectionConfig()
        self.config.apply_env_overrides()

        # Initialize Jev Client
        if jev_client:
            self.jev = jev_client
        else:
            api_key = self.config.api_key or os.getenv("TYPESAFE_API_KEY")
            self.jev = JevClient(
                api_key=api_key,
                base_url=self.config.base_url,
                model=self.config.model
            )

        # Destructive patterns regex
        escaped_keywords = [re.escape(k) for k in self.config.destructive_keywords]
        self.destructive_pattern = re.compile("|".join(escaped_keywords), re.IGNORECASE) if escaped_keywords else None

        # Alert manager
        self.alert_manager = AlertManager(
            webhook_url=self.config.alert.webhook_url,
            webhook_type=self.config.alert.webhook_type
        )

        os.makedirs(self.config.screenshot_dir, exist_ok=True)

        # Runtime states
        self.visited_signatures = set()
        self.executed_actions = []
        self.errors_found = []
        self.skipped_duplicates = []
        self.console_logs = []
        self.network_errors = []
        self.page_dialogs = []

        self._last_console_index = 0
        self._last_dialog_index = 0
        self._last_network_index = 0
        self.start_timestamp = 0.0
        self.end_timestamp = 0.0

    def _is_url_in_scope(self, url: str) -> bool:
        """Check if target URL belongs to allowed domains / root scope."""
        try:
            parsed = urlparse(url)
            start_parsed = urlparse(self.config.target_url)

            # Match start URL host
            if parsed.netloc == start_parsed.netloc:
                return True

            # Match user-configured allowed domains
            for domain in self.config.allowed_domains:
                if parsed.netloc == domain or parsed.netloc.endswith("." + domain):
                    return True
            return False
        except Exception:
            return False

    def _on_response(self, response: Response):
        """Intercept network responses to catch 4xx/5xx HTTP failures in real time."""
        try:
            status = response.status
            url = response.url
            # Ignore static assets like images, fonts, icons
            if status >= 400 and not url.endswith((".ico", ".svg", ".png", ".jpg", ".jpeg", ".woff2", ".ttf")):
                self.network_errors.append({
                    "url": url,
                    "status": status,
                    "status_text": response.status_text
                })
        except Exception:
            pass

    def _handle_dialog(self, dialog):
        msg = f"Dialog: {dialog.message}"
        self.page_dialogs.append(msg)
        logger.warning(f"[Browser Dialog] {msg}")
        try:
            dialog.accept()
        except Exception:
            pass

    def _extract_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract interactive candidate elements from DOM:
        Buttons, inputs, selects, textareas, links, tabs, and clickable components.
        Generates robust XPath, bounding box, semantic role, text label, and container pattern.
        """
        js_code = """
        () => {
            function getXPath(element) {
                if (element.id && element.id !== '') return `//*[@id="${element.id}"]`;
                if (element === document.body) return '/html/body';
                let ix = 0;
                let siblings = element.parentNode ? element.parentNode.childNodes : [];
                for (let i = 0; i < siblings.length; i++) {
                    let sibling = siblings[i];
                    if (sibling === element) {
                        return (element.parentNode ? getXPath(element.parentNode) : '') + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    }
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                        ix++;
                    }
                }
                return '';
            }

            function getContainerPattern(el) {
                let curr = el;
                let depth = 0;
                let containerType = 'standalone';
                let path = [];

                while (curr && curr !== document.body && depth < 8) {
                    let tag = curr.tagName.toLowerCase();
                    let cls = curr.className && typeof curr.className === 'string' 
                        ? curr.className.trim().split(/\\s+/).slice(0, 2).join('.') 
                        : '';
                    let identifier = cls ? `${tag}.${cls}` : tag;
                    path.unshift(identifier);

                    if (['tr', 'li'].includes(tag) || (cls && /(card|item|row|entry|post|list)/i.test(cls))) {
                        containerType = identifier;
                    }
                    curr = curr.parentElement;
                    depth++;
                }
                return {
                    fullPath: path.join(' > '),
                    containerType: containerType
                };
            }

            const candidates = [];
            const selector = 'button, a, input, select, textarea, [role="button"], [role="tab"], [role="link"], [role="menuitem"], [onclick]';
            const nodes = document.querySelectorAll(selector);

            nodes.forEach((el, index) => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || rect.width <= 3 || rect.height <= 3) {
                    return;
                }
                const tag = el.tagName.toLowerCase();
                const type = el.getAttribute('type') || '';
                const text = (el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
                const id = el.id || '';
                const name = el.name || '';
                const role = el.getAttribute('role') || '';
                const xpath = getXPath(el);
                const { fullPath, containerType } = getContainerPattern(el);

                candidates.push({
                    index,
                    tag,
                    type,
                    text: text.slice(0, 100),
                    id,
                    name,
                    role,
                    xpath,
                    pattern: fullPath,
                    containerType: containerType,
                    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true'
                });
            });
            return candidates;
        }
        """
        try:
            return page.evaluate(js_code)
        except Exception as e:
            logger.warning(f"Failed to extract DOM elements: {e}")
            return []

    def _generate_signature(self, el_info: Dict[str, Any]) -> str:
        """Generate structural and semantic fingerprint for duplicate detection."""
        pattern = el_info.get("pattern", "")
        tag = el_info.get("tag", "")
        role = el_info.get("role", "")
        text = el_info.get("text", "")
        el_id = el_info.get("id", "")
        container_type = el_info.get("containerType", "standalone")

        if container_type != "standalone" or any(s in pattern for s in ["table", "tbody", "tr", "ul > li", "ol > li", "card", "grid"]):
            norm_pattern = re.sub(r'\[\d+\]', '', pattern)
            return f"repeated_container|{tag}|role:{role}|container:{container_type}|path:{norm_pattern}"

        if el_id:
            return f"single|{tag}|id:{el_id}"
        return f"single|{tag}|text:{text[:24]}|pattern:{pattern}"

    def check_for_page_errors(self, page: Page, action_desc: str) -> Optional[Dict[str, Any]]:
        """
        Gathers evidence across DOM alerts, Toasts, Console logs, and Network 4xx/5xx responses.
        Submits structured prompt to Jev System One Model for typed classification.
        Captures screenshot if an error is verified.
        """
        error_extract_js = """
        () => {
            const potentialErrorEls = document.querySelectorAll(
                '.toast, .message, .alert, .notification, .error, .danger, .warning, [role="alert"], [class*="error"], [class*="alert"]'
            );
            const messages = [];
            potentialErrorEls.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                    return;
                }
                const text = (el.innerText || el.textContent || '').trim();
                if (text && text.length > 2 && text.length < 350) {
                    messages.push(text);
                }
            });
            return messages;
        }
        """
        found_texts = []
        try:
            dom_messages = page.evaluate(error_extract_js)
            found_texts.extend(dom_messages)
        except Exception:
            pass

        # 2. Console error logs
        recent_console = self.console_logs[self._last_console_index:]
        self._last_console_index = len(self.console_logs)
        for c in recent_console:
            lower_c = c.lower()
            if any(kw in lower_c for kw in ["error", "fail", "500", "400", "403", "404", "网络错误", "系统开小差", "错误请求"]):
                found_texts.append(f"Console: {c}")

        # 3. Network 4xx / 5xx responses
        recent_network = self.network_errors[self._last_network_index:]
        self._last_network_index = len(self.network_errors)
        for n in recent_network:
            found_texts.append(f"HTTP {n['status']} {n['status_text']} on {n['url']}")

        # 4. Browser dialog messages
        recent_dialogs = self.page_dialogs[self._last_dialog_index:]
        self._last_dialog_index = len(self.page_dialogs)
        for d in recent_dialogs:
            found_texts.append(f"Dialog: {d}")

        if not found_texts:
            return None

        # Deduplicate evidence
        unique_texts = list(dict.fromkeys(found_texts))
        combined_text = "\n".join(unique_texts)

        try:
            jev_res = self.jev.judge_error(combined_text)
        except Exception as e:
            logger.error(f"Jev judge_error failed: {e}")
            # Fallback local regex rule
            is_err = any(kw in combined_text.lower() for kw in ["500", "404", "crash", "error", "失败", "网络错误"])
            jev_res = {
                "is_error": is_err,
                "error_type": "request_error" if is_err else "normal_info",
                "confidence": 0.8 if is_err else 0.0,
                "severity_score": 0.7 if is_err else 0.0
            }

        if jev_res.get("is_error"):
            screenshot_path = ""
            try:
                fname = f"error_{int(time.time() * 1000)}.png"
                full_path = os.path.join(self.config.screenshot_dir, fname)
                page.screenshot(path=full_path, full_page=False)
                screenshot_path = full_path
            except Exception:
                pass

            error_record = {
                "action": action_desc,
                "detected_texts": unique_texts,
                "error_type": jev_res.get("error_type"),
                "jev_confidence": jev_res.get("confidence", 0.0),
                "severity_score": jev_res.get("severity_score", 0.0),
                "screenshot": screenshot_path,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.warning(
                f"[!] DETECTED ERROR: {error_record['error_type']} "
                f"(severity: {error_record['severity_score']:.2f}, conf: {error_record['jev_confidence']:.2f}) "
                f"at action: {action_desc}"
            )
            return error_record

        return None

    def _setup_authentication(self, context: BrowserContext, page: Page):
        """Perform automated login or inject cookies/session if configured."""
        auth = self.config.auth
        if not auth.enabled:
            return

        # Inject cookies
        if auth.cookies:
            context.add_cookies(auth.cookies)
            logger.info(f"Injected {len(auth.cookies)} session cookies")

        # Form-based login
        if auth.login_url and auth.username and auth.password:
            try:
                logger.info(f"Performing automatic login at {auth.login_url}")
                page.goto(auth.login_url, wait_until="domcontentloaded", timeout=self.config.page_load_timeout_ms)
                if auth.username_selector:
                    page.fill(auth.username_selector, auth.username)
                if auth.password_selector:
                    page.fill(auth.password_selector, auth.password)
                if auth.submit_selector:
                    page.click(auth.submit_selector)
                    page.wait_for_timeout(2000)
                logger.info("Authentication form submitted successfully")
            except Exception as e:
                logger.error(f"Authentication flow encountered error: {e}")

    def run(self) -> Dict[str, Any]:
        """
        Main execution loop for synthetic inspection.
        Returns complete inspection result dictionary.
        """
        self.start_timestamp = time.time()
        logger.info(f"Starting Web Synthetic Inspection on: {self.config.target_url}")
        logger.info(f"Headless: {self.config.headless} | Max Actions: {self.config.max_actions}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 (InspectionBot/1.0)"
            )
            page = context.new_page()

            page.on("console", lambda msg: self.console_logs.append(f"[{msg.type}] {msg.text}"))
            page.on("dialog", lambda dialog: self._handle_dialog(dialog))
            page.on("response", self._on_response)

            # Perform authentication if enabled
            self._setup_authentication(context, page)

            # Execute user journey flows if defined
            if self.config.flows:
                logger.info(f"Executing {len(self.config.flows)} predefined user journey flows...")
                flow_executor = FlowExecutor(page)
                for f_data in self.config.flows:
                    flow_def = FlowDefinition.from_dict(f_data)
                    flow_res = flow_executor.execute_flow(flow_def)
                    if flow_res.get("status") != "PASSED":
                        for err in flow_res.get("errors", []):
                            self.errors_found.append({
                                "action": f"Flow '{flow_def.name}'",
                                "detected_texts": [err.get("error", "")],
                                "error_type": "flow_assertion_failure",
                                "jev_confidence": 1.0,
                                "severity_score": 0.9,
                                "screenshot": "",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })

            # Load target page
            try:
                page.goto(self.config.target_url, wait_until="domcontentloaded", timeout=self.config.page_load_timeout_ms)
                page.wait_for_timeout(1500)
            except Exception as e:
                logger.error(f"Initial page load failed: {e}")
                self.errors_found.append({
                    "action": "initial_page_load",
                    "detected_texts": [str(e)],
                    "error_type": "network_error",
                    "jev_confidence": 1.0,
                    "severity_score": 1.0,
                    "screenshot": "",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })

            # Check for initial page errors
            initial_err = self.check_for_page_errors(page, "initial_page_load")
            if initial_err:
                self.errors_found.append(initial_err)

            action_count = 0
            consecutive_failures = 0

            # Main interactive traversal loop
            while action_count < self.config.max_actions:
                if consecutive_failures >= self.config.max_consecutive_failures:
                    logger.error(f"Reached {self.config.max_consecutive_failures} consecutive failures. Aborting traversal loop.")
                    break

                elements = self._extract_interactive_elements(page)
                if not elements:
                    logger.info("No interactive elements discovered on page.")
                    break

                target_candidate = None
                target_signature = None

                for el in elements:
                    if el.get("disabled"):
                        continue

                    # Safety Guard: Skip destructive operations
                    el_text = el.get("text", "")
                    if self.destructive_pattern and self.destructive_pattern.search(el_text):
                        logger.info(f"Skipping destructive button/action: '{el_text}'")
                        continue

                    sig = self._generate_signature(el)
                    summary = f"Tag: <{el['tag']}>, Text: '{el_text}', Container: '{el.get('containerType')}', Pattern: '{el['pattern']}'"

                    # 1. Structural Fingerprint Check
                    if sig in self.visited_signatures:
                        self.skipped_duplicates.append({
                            "element": summary,
                            "reason": "Structural fingerprint matches already tested container type",
                            "signature": sig
                        })
                        continue

                    # 2. Jev Semantic Redundancy Check
                    if self.config.use_jev_dedup and len(self.visited_signatures) > 0 and (len(self.visited_signatures) % 4 == 0):
                        should_skip = self.jev.should_skip_duplicate(summary, list(self.visited_signatures))
                        if should_skip:
                            self.skipped_duplicates.append({
                                "element": summary,
                                "reason": "Jev semantic evaluation determined as redundant duplicate data",
                                "signature": sig
                            })
                            self.visited_signatures.add(sig)
                            continue

                    target_candidate = el
                    target_signature = sig
                    break

                if not target_candidate:
                    logger.info("All interactive element categories explored without redundant repeats.")
                    break

                # Interacting with candidate
                self.visited_signatures.add(target_signature)
                action_desc = f"{target_candidate['tag']}['{target_candidate['text']}'] (xpath: {target_candidate['xpath']})"
                logger.info(f"Action #{action_count + 1}/{self.config.max_actions}: Interacting with {action_desc}")

                action_success = False
                try:
                    locator = page.locator(f"xpath={target_candidate['xpath']}").first
                    tag = target_candidate['tag']
                    input_type = target_candidate['type']

                    try:
                        locator.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass

                    if tag == "input" and input_type in ["text", "password", "email", "search", "number", "tel"]:
                        locator.fill("inspection_test_input", timeout=self.config.action_timeout_ms)
                    elif tag == "select":
                        try:
                            locator.select_option(index=1, timeout=self.config.action_timeout_ms)
                        except Exception:
                            locator.click(timeout=self.config.action_timeout_ms)
                    else:
                        locator.click(timeout=self.config.action_timeout_ms)

                    action_success = True
                    consecutive_failures = 0
                    self.executed_actions.append({
                        "step": action_count + 1,
                        "action": action_desc,
                        "status": "success",
                        "signature": target_signature
                    })
                except Exception as ex:
                    consecutive_failures += 1
                    logger.warning(f"Interaction step failed: {ex}")
                    self.executed_actions.append({
                        "step": action_count + 1,
                        "action": action_desc,
                        "status": f"failed: {str(ex)}",
                        "signature": target_signature
                    })

                action_count += 1
                time.sleep(self.config.wait_after_action)

                # Check for errors after each action
                err = self.check_for_page_errors(page, action_desc)
                if err:
                    self.errors_found.append(err)

                # Domain / scope guard: Return to start URL if navigated out of scope
                try:
                    curr_url = page.url
                    if not self._is_url_in_scope(curr_url):
                        logger.info(f"Navigated outside allowed scope ({curr_url}). Navigating back...")
                        page.go_back(wait_until="domcontentloaded", timeout=5000)
                except Exception:
                    pass

                # Clear temporary dismissible alerts
                try:
                    page.evaluate("""() => {
                        const b = document.getElementById('toast-box') || document.querySelector('.toast, .alert-dismissible');
                        if (b) b.style.display = 'none';
                    }""")
                except Exception:
                    pass

            browser.close()

        self.end_timestamp = time.time()
        result = self._save_and_report()
        return result

    def _save_and_report(self) -> Dict[str, Any]:
        duration = round(self.end_timestamp - self.start_timestamp, 2)
        summary = {
            "target_url": self.config.target_url,
            "duration_seconds": duration,
            "total_actions_executed": len(self.executed_actions),
            "total_duplicates_skipped": len(self.skipped_duplicates),
            "total_errors_detected": len(self.errors_found),
            "status": "FAILED" if self.errors_found else "PASSED",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        report = {
            "summary": summary,
            "errors_detected": self.errors_found,
            "executed_actions": self.executed_actions,
            "skipped_duplicates": self.skipped_duplicates
        }

        # 1. Save JSON Report
        if self.config.report_json_path:
            with open(self.config.report_json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved inspection JSON report to {self.config.report_json_path}")

        # 2. Generate HTML Report
        try:
            from generate_report import generate_html_report
            import glob
            json_files = glob.glob("report_*.json") + [self.config.report_json_path]
            generate_html_report(list(set(json_files)), self.config.report_html_path)
            logger.info(f"Updated HTML report at {self.config.report_html_path}")
        except Exception as e:
            logger.warning(f"Failed to compile HTML report: {e}")

        # 3. Trigger Alert if configured and errors detected
        if self.config.alert.enabled and self.errors_found:
            self.alert_manager.send_alert(
                title=f"线上巡检异常发现 ({self.config.target_url})",
                summary=summary,
                errors=self.errors_found
            )

        # 4. Generate Prometheus Metrics file
        self._export_prometheus_metrics(summary)

        logger.info("="*50)
        logger.info(f"Inspection Run Summary: Status={summary['status']}, Actions={summary['total_actions_executed']}, Errors={summary['total_errors_detected']}, Time={duration}s")
        logger.info("="*50)

        return report

    def _export_prometheus_metrics(self, summary: Dict[str, Any], filepath: str = "inspection_metrics.prom"):
        """Export Prometheus metrics for node_exporter or Pushgateway ingestion."""
        lines = [
            "# HELP web_inspection_status Inspection result status (1 = passed, 0 = failed)",
            "# TYPE web_inspection_status gauge",
            f'web_inspection_status{{target="{summary["target_url"]}"}} {1 if summary["status"] == "PASSED" else 0}',
            "# HELP web_inspection_errors_total Total errors detected during inspection",
            "# TYPE web_inspection_errors_total counter",
            f'web_inspection_errors_total{{target="{summary["target_url"]}"}} {summary["total_errors_detected"]}',
            "# HELP web_inspection_actions_total Total actions executed during inspection",
            "# TYPE web_inspection_actions_total counter",
            f'web_inspection_actions_total{{target="{summary["target_url"]}"}} {summary["total_actions_executed"]}',
            "# HELP web_inspection_duration_seconds Inspection run duration in seconds",
            "# TYPE web_inspection_duration_seconds gauge",
            f'web_inspection_duration_seconds{{target="{summary["target_url"]}"}} {summary["duration_seconds"]}\n'
        ]
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            logger.warning(f"Failed to write prometheus metrics: {e}")

# Backward compatibility alias
WebCrawler = WebInspectionCrawler
