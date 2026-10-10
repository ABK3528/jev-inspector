"""
Jev Client wrapper for TypeSafe System One Decision Model.
API Endpoint: https://api.typesafe.ai/v1/systemone
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

DEFAULT_API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"

class JevClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_API_URL, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        self.base_url = base_url
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def evaluate(self, state: str, questions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send state and typed questions to Jev.
        Questions format:
          {
            "q_name": {"type": "noul", "instructions": "..."},
            "q_choice": {"type": "choice", "instructions": "...", "criteria": {"k": "v", ...}},
            "q_score": {"type": "score", "instructions": "...", "criteria": ["low", "mid", "high"]}
          }
        """
        payload = {
            "model": self.model,
            "state": state,
            "questions": questions
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise RuntimeError(f"Jev API HTTP Error {e.code}: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"Jev API request failed: {e}") from e

    def judge_error(self, page_feedback: str) -> Dict[str, Any]:
        """
        Use Jev Noul, Choice, and Score in a single fan-out request to evaluate whether
        the page feedback indicates an error, its specific category, and its severity level.
        Distinguishes genuine errors ('网络错误', '系统开小差', '错误请求', 500, 400)
        from normal browser warnings or benign logs.
        """
        if not page_feedback or len(page_feedback.strip()) < 2:
            return {"is_error": False, "probability": 0.0, "error_type": "normal_info", "severity": 0}

        # Truncate to reasonable length for System One fast decision
        truncated_state = page_feedback[:1200]
        state = f"Observed Feedback / Toast / Console / Network status:\n'''\n{truncated_state}\n'''"
        
        questions = {
            "is_error": {
                "type": "noul",
                "instructions": "Does the observed text indicate an error, crash, malfunction, failed request, or system glitch (e.g. '网络错误', '系统开小差', '错误请求', '请求失败', '500 Internal Server Error', '404 Not Found', 'Network connection failed') rather than normal operation or harmless webgl/feature deprecation warning?"
            },
            "error_type": {
                "type": "choice",
                "instructions": "Which exact category best describes this message?",
                "criteria": {
                    "network_error": "Network unreachable, timeout, connection reset, or DNS failure (网络错误)",
                    "system_error": "Backend crash, unhandled 5xx exception, server glitch ('系统开小差')",
                    "request_error": "Bad client request, 400 invalid params, 403 forbidden, 404 not found ('错误请求')",
                    "browser_noise": "Harmless browser warning, deprecated CSS/WebGL property, or benign security policy hint",
                    "normal_info": "Normal operation notice, success message, or informational toast"
                }
            },
            "severity": {
                "type": "score",
                "instructions": "How severe is this issue for end users?",
                "criteria": ["benign", "minor_warning", "major_error", "critical_crash"]
            }
        }
        res = self.evaluate(state, questions)
        answers = res.get("answers", {})
        
        is_err_prob = answers.get("is_error", {}).get("noul", 0.0)
        err_type = answers.get("error_type", {}).get("choice", "normal_info")
        type_conf = answers.get("error_type", {}).get("confidence", 0.0)
        severity_score = answers.get("severity", {}).get("score", 0.0)

        # A true error must not be browser noise or normal info
        is_real_error = (
            (is_err_prob >= 0.70 and err_type not in ["browser_noise", "normal_info"]) or
            (err_type in ["network_error", "system_error", "request_error"] and type_conf >= 0.60)
        )

        return {
            "is_error": is_real_error,
            "probability": is_err_prob,
            "error_type": err_type,
            "confidence": type_conf,
            "severity_score": severity_score,
            "details": answers
        }

    def should_skip_duplicate(self, element_summary: str, seen_signatures: list[str]) -> bool:
        """
        Given an element summary and already tested element types/patterns,
        evaluate if this element is a duplicate of the same type and should be skipped.
        """
        if not seen_signatures:
            return False
        state = f"Current Element: {element_summary}\nAlready executed element signatures:\n" + "\n".join(f"- {s}" for s in seen_signatures[-15:])
        questions = {
            "is_redundant_duplicate": {
                "type": "noul",
                "instructions": "Is the current element an identical functional duplicate of one of the already executed element signatures (e.g. repeated item in a list/table with identical behavior, or identical pagination link) that does not need repeat testing?"
            }
        }
        try:
            res = self.evaluate(state, questions)
            prob = res.get("answers", {}).get("is_redundant_duplicate", {}).get("noul", 0.0)
            return prob >= 0.70
        except Exception:
            # Fallback to local heuristic if network glitch
            return False
