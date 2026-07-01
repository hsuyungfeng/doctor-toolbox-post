#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firecrawl Scraper Client (Local self-hosted version)
- Connects to local Firecrawl API (default: http://localhost:3002)
- Scrapes clinic websites to extract Markdown, Links, Emails, and FB URLs
"""

import json
import re
import urllib.request
import urllib.error
from pathlib import Path

# === Configuration ===
LOCAL_FIRECRAWL_URL = "http://localhost:3002"

def scrape_url_local(target_url, firecrawl_api_url=LOCAL_FIRECRAWL_URL):
    """
    Scrapes a single URL using local Firecrawl /v1/scrape endpoint.
    Returns dictionary with parsed data.
    """
    endpoint = f"{firecrawl_api_url.rstrip('/')}/v1/scrape"
    headers = {"Content-Type": "application/json"}
    payload = {
        "url": target_url,
        "formats": ["markdown", "links"],
        "onlyMainContent": True
    }
    
    print(f"🌐 [Local Firecrawl] Scraping: {target_url}...")
    try:
        req = urllib.request.Request(
            endpoint, 
            data=json.dumps(payload).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            if res_data.get("success") and "data" in res_data:
                data = res_data["data"]
                markdown = data.get("markdown", "")
                links = data.get("links", [])
                metadata = data.get("metadata", {})
                
                # Extract contacts
                emails = extract_emails(markdown)
                facebook_links = extract_facebook_links(links, markdown)
                
                return {
                    "success": True,
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "markdown": markdown,
                    "emails": list(emails),
                    "facebook_links": list(facebook_links),
                    "raw_data": data
                }
            else:
                return {"success": False, "error": res_data.get("error", "Unknown API error")}
                
    except urllib.error.URLError as e:
        return {
            "success": False, 
            "error": f"Failed to connect to local Firecrawl at {endpoint}. Ensure docker container is running. Error: {e}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_emails(text):
    """Extracts all email addresses from text using regex."""
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    return set(email_pattern.findall(text))

def extract_facebook_links(links, markdown_text):
    """Extracts Facebook page links from crawled links and markdown text."""
    fb_links = set()
    fb_pattern = re.compile(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._%+-/]+')
    
    # 1. Search in crawled links list
    for link in links:
        if "facebook.com" in link:
            # Clean up tracking params
            clean_url = link.split('?')[0].rstrip('/')
            # Filter out sharing/apps links
            if not any(x in clean_url for x in ['sharer', 'share.php', 'plugins', 'dialog']):
                fb_links.add(clean_url)
                
    # 2. Search in markdown text as fallback
    matches = fb_pattern.findall(markdown_text)
    for match in matches:
        clean_url = match.split('?')[0].split(')')[0].split(']')[0].rstrip('/')
        if not any(x in clean_url for x in ['sharer', 'share.php', 'plugins', 'dialog']):
            fb_links.add(clean_url)
            
    return fb_links

if __name__ == "__main__":
    # Quick CLI test
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(f"Testing local Firecrawl scraper client on: {url}")
    result = scrape_url_local(url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
