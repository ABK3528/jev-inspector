#!/usr/bin/env python3
"""
Test traversal against diverse public websites with real UI components.
"""

import os
from jev_client import JevClient
from crawler import WebCrawler

API_KEY = os.getenv("TYPESAFE_API_KEY")

SITES = [
    {
        "name": "Wikipedia Main Page (Global Portal & Navigation)",
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "report": "report_wikipedia.json",
        "max_actions": 15
    },
    {
        "name": "Python Official Website (Documentation & Search)",
        "url": "https://www.python.org/",
        "report": "report_python.json",
        "max_actions": 15
    },
    {
        "name": "V2EX (Forum & Community Lists)",
        "url": "https://www.v2ex.com/",
        "report": "report_v2ex.json",
        "max_actions": 15
    }
]

def main():
    client = JevClient(api_key=API_KEY)
    for site in SITES:
        print("\n" + "="*65)
        print(f"[*] Testing: {site['name']}")
        print(f"    URL: {site['url']}")
        print("="*65)
        crawler = WebCrawler(
            start_url=site["url"],
            jev_client=client,
            headless=True,
            max_actions=site["max_actions"],
            output_report=site["report"]
        )
        crawler.run()

if __name__ == "__main__":
    main()
