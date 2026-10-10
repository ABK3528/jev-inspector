"""
Multi-Step User Journey Flow & Custom Assertion Engine.
Complements AI-driven autonomous exploration with deterministic, critical-path synthetic flows:
- Multi-step sequential actions (goto, click, fill, select, hover, wait_for_selector, assert)
- Rich assertions: text contains, title equals, url matches, element visible, response status, SLA response time
- SLA & Performance latency threshold verification
- Clean integration with existing Crawler and Scheduler
"""

import time
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from playwright.sync_api import Page, Response, BrowserContext

logger = logging.getLogger("inspection.flow")

@dataclass
class FlowStep:
    """Represents a single step in a multi-step user journey."""
    action: str  # goto, click, fill, select, hover, wait, assert, scroll
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout_ms: int = 5000
    description: Optional[str] = None
    # Assertion specific parameters
    assert_type: Optional[str] = None  # text_contains, visible, title_matches, url_matches, status_ok
    expected: Optional[str] = None


@dataclass
class FlowDefinition:
    """Complete user journey definition."""
    name: str
    description: str = ""
    start_url: str = ""
    steps: List[FlowStep] = field(default_factory=list)
    sla_max_duration_seconds: float = 30.0
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowDefinition":
        steps_raw = data.get("steps", [])
        steps = []
        for s in steps_raw:
            steps.append(FlowStep(
                action=s.get("action", "click"),
                selector=s.get("selector"),
                value=s.get("value"),
                timeout_ms=s.get("timeout_ms", 5000),
                description=s.get("description"),
                assert_type=s.get("assert_type"),
                expected=s.get("expected")
            ))
        return cls(
            name=data.get("name", "Unnamed Flow"),
            description=data.get("description", ""),
            start_url=data.get("start_url", ""),
            steps=steps,
            sla_max_duration_seconds=data.get("sla_max_duration_seconds", 30.0),
            tags=data.get("tags", [])
        )


class FlowExecutor:
    """Executes a defined user journey flow on a Playwright Page/Context with assertions,
    timing, and multi-page/tab switching support."""

    def __init__(self, page: Page, context: Optional[BrowserContext] = None):
        self.page = page
        self.context = context or page.context
        self.named_pages: Dict[str, Page] = {"main": page}
        self.page_stack: List[Page] = [page]

    def execute_flow(self, flow: FlowDefinition) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Starting User Journey Flow: '{flow.name}' ({len(flow.steps)} steps)")
        
        step_results = []
        errors = []

        if flow.start_url:
            try:
                t0 = time.time()
                self.page.goto(flow.start_url, wait_until="domcontentloaded", timeout=15000)
                step_results.append({
                    "step_index": 0,
                    "action": "goto",
                    "target": flow.start_url,
                    "status": "PASSED",
                    "latency_ms": round((time.time() - t0) * 1000, 2)
                })
            except Exception as e:
                err_msg = f"Failed to navigate to flow start URL '{flow.start_url}': {e}"
                logger.error(err_msg)
                errors.append({"action": "goto", "error": err_msg})
                return self._build_result(flow, start_time, step_results, errors)

        for idx, step in enumerate(flow.steps, start=1):
            t0 = time.time()
            desc = step.description or f"{step.action} on {step.selector or step.value or 'page'}"
            logger.info(f"  Step {idx}/{len(flow.steps)}: {desc}")
            
            try:
                self._execute_step(step)
                latency = round((time.time() - t0) * 1000, 2)
                step_results.append({
                    "step_index": idx,
                    "description": desc,
                    "action": step.action,
                    "status": "PASSED",
                    "latency_ms": latency
                })
            except Exception as e:
                latency = round((time.time() - t0) * 1000, 2)
                err_msg = f"Step {idx} ({desc}) failed: {e}"
                logger.error(err_msg)
                step_results.append({
                    "step_index": idx,
                    "description": desc,
                    "action": step.action,
                    "status": "FAILED",
                    "error": str(e),
                    "latency_ms": latency
                })
                errors.append({
                    "step": idx,
                    "description": desc,
                    "error": str(e)
                })
                # Abort remaining steps on step failure
                break

        duration = time.time() - start_time
        # Check SLA threshold
        if flow.sla_max_duration_seconds and duration > flow.sla_max_duration_seconds:
            sla_err = f"Flow execution exceeded SLA threshold ({duration:.2f}s > {flow.sla_max_duration_seconds:.2f}s)"
            logger.warning(sla_err)
            errors.append({"action": "sla_check", "error": sla_err})

        return self._build_result(flow, start_time, step_results, errors)

    def _execute_step(self, step: FlowStep):
        action = step.action.lower()

        if action == "goto":
            self.page.goto(step.value, wait_until="domcontentloaded", timeout=step.timeout_ms)

        elif action == "click":
            locator = self.page.locator(step.selector).first
            locator.scroll_into_view_if_needed(timeout=step.timeout_ms)
            locator.click(timeout=step.timeout_ms)

        elif action == "fill":
            locator = self.page.locator(step.selector).first
            locator.scroll_into_view_if_needed(timeout=step.timeout_ms)
            locator.fill(step.value or "", timeout=step.timeout_ms)

        elif action == "select":
            locator = self.page.locator(step.selector).first
            locator.select_option(value=step.value, timeout=step.timeout_ms)

        elif action == "hover":
            locator = self.page.locator(step.selector).first
            locator.hover(timeout=step.timeout_ms)

        elif action == "wait":
            wait_sec = float(step.value or 1.0)
            time.sleep(wait_sec)

        elif action == "assert":
            self._assert_condition(step)

        # Multi-tab / Page switching actions
        elif action == "click_and_expect_page":
            # Click an element (e.g. target="_blank" or window.open) and wait for the new page
            page_alias = step.value or f"tab_{len(self.named_pages)}"
            with self.context.expect_page(timeout=step.timeout_ms) as new_page_info:
                locator = self.page.locator(step.selector).first
                locator.scroll_into_view_if_needed(timeout=step.timeout_ms)
                locator.click(timeout=step.timeout_ms)
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded", timeout=step.timeout_ms)
            self.named_pages[page_alias] = new_page
            self.page_stack.append(new_page)
            self.page = new_page  # Switch current active page to new page
            logger.info(f"Switched active page to newly opened tab: '{page_alias}' (URL: {new_page.url})")

        elif action == "open_tab":
            # Explicitly open a new tab with given URL
            page_alias = step.selector or f"tab_{len(self.named_pages)}"
            url = step.value
            new_page = self.context.new_page()
            if url:
                new_page.goto(url, wait_until="domcontentloaded", timeout=step.timeout_ms)
            self.named_pages[page_alias] = new_page
            self.page_stack.append(new_page)
            self.page = new_page
            logger.info(f"Opened new tab: '{page_alias}' (URL: {url})")

        elif action == "switch_tab":
            # Switch active page to target alias or index
            target = step.value or "main"
            if target in self.named_pages:
                self.page = self.named_pages[target]
            elif target == "previous" and len(self.page_stack) > 1:
                self.page_stack.pop()
                self.page = self.page_stack[-1]
            elif target.isdigit():
                idx = int(target)
                all_pages = self.context.pages
                if 0 <= idx < len(all_pages):
                    self.page = all_pages[idx]
                else:
                    raise IndexError(f"Page index {idx} out of range (total pages: {len(all_pages)})")
            else:
                raise ValueError(f"Unknown page target: '{target}'. Available tabs: {list(self.named_pages.keys())}")
            self.page.bring_to_front()
            logger.info(f"Switched active page to tab '{target}' (URL: {self.page.url})")

        elif action == "close_tab":
            # Close target tab or current active tab
            target = step.value
            target_page = self.named_pages.get(target) if target else self.page
            if target_page:
                try:
                    target_page.close()
                except Exception:
                    pass
                # Remove from tracking
                for k, v in list(self.named_pages.items()):
                    if v == target_page:
                        del self.named_pages[k]
                if target_page in self.page_stack:
                    self.page_stack.remove(target_page)
                # Reset active page
                self.page = self.page_stack[-1] if self.page_stack else (self.context.pages[0] if self.context.pages else None)
                if self.page:
                    self.page.bring_to_front()
                logger.info(f"Closed tab. Active page now set to: {getattr(self.page, 'url', 'None')}")

        else:
            raise ValueError(f"Unsupported flow action: '{step.action}'")

    def _assert_condition(self, step: FlowStep):
        atype = (step.assert_type or "").lower()
        expected = step.expected or ""

        if atype == "text_contains":
            locator = self.page.locator(step.selector).first
            text = locator.inner_text(timeout=step.timeout_ms)
            if expected not in text:
                raise AssertionError(f"Expected text '{expected}' not found in element '{step.selector}' (actual: '{text}')")

        elif atype == "visible":
            locator = self.page.locator(step.selector).first
            if not locator.is_visible():
                raise AssertionError(f"Element '{step.selector}' is not visible on page")

        elif atype == "title_matches":
            title = self.page.title()
            if not re.search(expected, title):
                raise AssertionError(f"Page title '{title}' did not match pattern '{expected}'")

        elif atype == "url_matches":
            url = self.page.url
            if not re.search(expected, url):
                raise AssertionError(f"Page url '{url}' did not match pattern '{expected}'")

        else:
            raise ValueError(f"Unsupported assertion type: '{step.assert_type}'")

    def _build_result(self, flow: FlowDefinition, start_time: float, steps: List[Dict[str, Any]], errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        duration = round(time.time() - start_time, 2)
        status = "PASSED" if not errors else "FAILED"
        return {
            "flow_name": flow.name,
            "status": status,
            "duration_seconds": duration,
            "sla_threshold_seconds": flow.sla_max_duration_seconds,
            "sla_breached": duration > flow.sla_max_duration_seconds,
            "total_steps": len(flow.steps),
            "executed_steps": len(steps),
            "errors": errors,
            "step_results": steps,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
