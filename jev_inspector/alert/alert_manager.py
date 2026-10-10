"""
Inspection Alerting & Notification Engine for Online Synthetic Monitoring.
Supports Webhook (Slack/Discord/Enterprise WeChat/Feishu/DingTalk/Generic),
console alerting, and incident severity routing.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("inspection.alerts")

class AlertManager:
    def __init__(self, webhook_url: Optional[str] = None, webhook_type: str = "generic"):
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type.lower()
        self.alert_history: List[Dict[str, Any]] = []

    def format_payload(self, title: str, summary: Dict[str, Any], errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        
        # 1. Feishu / Lark format
        if self.webhook_type in ["feishu", "lark"]:
            error_lines = "\n".join([f"• [{e.get('error_type', 'ERROR')}] {e.get('action', '')}: {str(e.get('detected_texts', []))[:120]}" for e in errors[:5]])
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": f"🚨 [线上巡检告警] {title}"},
                        "template": "red" if errors else "green"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**目标地址**: {summary.get('target_url')}\n**状态**: {'异常' if errors else '正常'}\n**执行动作数**: {summary.get('total_actions_executed')}\n**检出异常数**: {len(errors)}\n**时间**: {timestamp}\n\n**异常明细**:\n{error_lines if errors else '无异常'}"
                            }
                        }
                    ]
                }
            }

        # 2. DingTalk format
        elif self.webhook_type == "dingtalk":
            markdown_text = f"### 🚨 线上巡检告警: {title}\n\n- **目标**: {summary.get('target_url')}\n- **异常数**: {len(errors)}\n- **动作数**: {summary.get('total_actions_executed')}\n- **时间**: {timestamp}\n"
            for e in errors[:5]:
                markdown_text += f"\n> **{e.get('error_type')}**: {e.get('action')} (严重度: {e.get('severity_score', 0):.2f})\n"
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"线上巡检告警: {title}",
                    "text": markdown_text
                }
            }

        # 3. WeCom (Enterprise WeChat) format
        elif self.webhook_type in ["wecom", "work_wechat"]:
            content = f"【线上巡检告警】{title}\n目标: {summary.get('target_url')}\n异常数: {len(errors)}\n时间: {timestamp}\n"
            for e in errors[:5]:
                content += f"\n- {e.get('error_type')}: {e.get('action')}"
            return {
                "msgtype": "text",
                "text": {"content": content}
            }

        # 4. Slack format
        elif self.webhook_type == "slack":
            fields = [
                {"type": "mrkdwn", "text": f"*URL:*\n{summary.get('target_url')}"},
                {"type": "mrkdwn", "text": f"*Errors:*\n{len(errors)}"},
                {"type": "mrkdwn", "text": f"*Actions:*\n{summary.get('total_actions_executed')}"},
                {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"}
            ]
            return {
                "text": f"🚨 [Web Inspection Alert] {title}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*🚨 Web Inspection Alert: {title}*"}
                    },
                    {"type": "section", "fields": fields}
                ]
            }

        # Generic JSON payload
        return {
            "title": title,
            "status": "ALERT" if errors else "OK",
            "timestamp": timestamp,
            "summary": summary,
            "errors": errors
        }

    def send_alert(self, title: str, summary: Dict[str, Any], errors: List[Dict[str, Any]]) -> bool:
        """Send notification via configured webhook."""
        if not self.webhook_url:
            logger.info("No alert webhook configured. Alert dispatch skipped.")
            return False

        payload = self.format_payload(title, summary, errors)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                success = (resp.status in [200, 201, 204])
                self.alert_history.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title,
                    "success": success,
                    "status_code": resp.status
                })
                logger.info(f"Alert delivered successfully (HTTP {resp.status})")
                return success
        except Exception as e:
            logger.error(f"Failed to deliver alert webhook: {e}")
            self.alert_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "title": title,
                "success": False,
                "error": str(e)
            })
            return False
