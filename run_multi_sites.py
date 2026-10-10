#!/usr/bin/env python3
"""
Multi-site traversal test script using real public websites.
"""

import os
from jev_client import JevClient
from crawler import WebCrawler

API_KEY = os.getenv("TYPESAFE_API_KEY")

TEST_SITES = [
    {
        "name": "Quotes To Scrape (Quotes & Tag Elements, Repetitive Cards)",
        "url": "https://quotes.toscrape.com/",
        "report": "report_quotes.json",
        "max_actions": 15
    },
    {
        "name": "HTTPBin HTML Forms (Form Inputs, Radio, Checkboxes)",
        "url": "https://httpbin.org/forms/post",
        "report": "report_httpbin_form.json",
        "max_actions": 12
    },
    {
        "name": "Hacker News (Listing, Repetitive Links & Vote Elements)",
        "url": "https://news.ycombinator.com/",
        "report": "report_hackernews.json",
        "max_actions": 10
    }
]

def main():
    client = JevClient(api_key=API_KEY)
    for site in TEST_SITES:
        print("\n" + "="*60)
        print(f"Traversing: {site['name']} -> {site['url']}")
        print("="*60)
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
