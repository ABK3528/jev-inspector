# CLAUDE.md — Claude Code Engineering Guidelines for pi_test

This project adopts Anthropic **Claude Code** operational standards for software engineering.

## Commands
- Run Crawler: `python3 crawler.py`
- Run Multi-site Test: `python3 run_multi_sites.py`
- Run Real Websites: `python3 run_real_websites.py`
- Generate HTML Reports: `python3 generate_report.py`

## Engineering Posture
1. **Direct Execution**: Do not explain trivial steps; read files, edit lines, run checks, and present results.
2. **Context Precision**: Use `read` with line bounds and `grep` with regex to locate symbols quickly without bloating context.
3. **Surgical Edits**: Use exact match edits (`edit`), avoid wholesale file rewrites, and verify changes via tests immediately.
4. **Clean Code**: Keep Python code idiomatic, type-hinted where helpful, and error-handled.
5. **Self-Healing Loop**: Inspect tracebacks proactively on command failure, fix the root cause, and re-run verification before reporting status.
6. **Token & Context Economy**: Keep terminal command outputs focused; paginate long logs to prevent context bloat.
