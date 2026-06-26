#!/usr/bin/env python3
"""
Test script to scrape Email and Messenger info from a Facebook page.
Uses the persistent profile from `./browser_profile`.
Target page: https://www.facebook.com/wenxin22636645/ (文星外科診所)
"""
import time
import re
import os
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR.parent / "browser_profile"

TARGET_URL = "https://www.facebook.com/wenxin22636645/"

def extract_facebook_info(page, url):
    print(f"\n🔵 載入頁面: {url}")
    page.goto(url)
    time.sleep(6)
    page.screenshot(path="/tmp/fb_scrape_main.png")
    
    # Try to extract from main page content (Intro/Sidebar)
    info = page.evaluate("""() => {
        const results = {
            emails: [],
            messenger_links: [],
            phones: [],
            websites: [],
            username: ''
        };
        
        // Helper to extract email regex
        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
        
        // 1. Scan mailto links
        document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
            const email = a.getAttribute('href').replace('mailto:', '').split('?')[0].trim();
            if (email && !results.emails.includes(email)) {
                results.emails.push(email);
            }
        });
        
        // 2. Scan all page text for email patterns
        const pageText = document.body.innerText;
        const matchedEmails = pageText.match(emailRegex);
        if (matchedEmails) {
            matchedEmails.forEach(email => {
                const cleaned = email.trim();
                if (cleaned && !results.emails.includes(cleaned)) {
                    results.emails.push(cleaned);
                }
            });
        }
        
        // 3. Scan for messenger links
        document.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href') || '';
            if (href.includes('m.me/') || href.includes('messenger.com/t/')) {
                let cleanHref = href.split('?')[0].trim();
                if (!results.messenger_links.includes(cleanHref)) {
                    results.messenger_links.push(cleanHref);
                }
            }
        });
        
        // 4. Scan page source/text for phone number patterns
        // Usually listed as 04-22636645 or similar
        const phoneRegex = /(0\\d{1,2}-\\d{7,8})|(\\(0\\d\\)\\d{7,8})|(\\+886\\d{8,9})/g;
        const matchedPhones = pageText.match(phoneRegex);
        if (matchedPhones) {
            matchedPhones.forEach(p => {
                const cleaned = p.trim();
                if (cleaned && !results.phones.includes(cleaned)) {
                    results.phones.push(cleaned);
                }
            });
        }
        
        // 5. Look for external websites
        document.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href') || '';
            const text = (a.textContent || '').trim();
            if (href.includes('l.facebook.com/l.php?u=')) {
                let urlParam = new URL(href).searchParams.get('u');
                if (urlParam) {
                    urlParam = decodeURIComponent(urlParam).split('?')[0];
                    if (!urlParam.includes('facebook.com') && !urlParam.includes('instagram.com') && !results.websites.includes(urlParam)) {
                        results.websites.push(urlParam);
                    }
                }
            }
        });
        
        return results;
    }""")
    
    # Try getting the username or page ID from the URL or metadata
    page_username = ""
    parsed_url = re.search(r'facebook\.com/([^/?]+)', url)
    if parsed_url:
        page_username = parsed_url.group(1)
        if page_username == "profile.php" or page_username == "p":
            # For p-style pages, check pathname
            p_match = re.search(r'facebook\.com/p/([^/?]+)', url)
            if p_match:
                page_username = p_match.group(1)
    
    info['username'] = page_username
    if page_username and not any('m.me/' in link for link in info['messenger_links']):
        info['messenger_links'].append(f"https://m.me/{page_username}")
        
    print("📋 主頁面提取結果:")
    print(f"  - Emails: {info['emails']}")
    print(f"  - Messenger: {info['messenger_links']}")
    print(f"  - Phones: {info['phones']}")
    print(f"  - Websites: {info['websites']}")
    
    # If no email is found, navigate to the about page
    if not info['emails']:
        about_url = url.rstrip('/') + '/about'
        print(f"\n🔄 未找到 Email，導航至 About 頁面: {about_url}")
        page.goto(about_url)
        time.sleep(5)
        page.screenshot(path="/tmp/fb_scrape_about.png")
        
        about_info = page.evaluate("""() => {
            const results = {
                emails: []
            };
            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
            
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.getAttribute('href').replace('mailto:', '').split('?')[0].trim();
                if (email && !results.emails.includes(email)) {
                    results.emails.push(email);
                }
            });
            
            const pageText = document.body.innerText;
            const matchedEmails = pageText.match(emailRegex);
            if (matchedEmails) {
                matchedEmails.forEach(email => {
                    const cleaned = email.trim();
                    if (cleaned && !results.emails.includes(cleaned)) {
                        results.emails.push(cleaned);
                    }
                });
            }
            return results;
        }""")
        
        info['emails'] = list(set(info['emails'] + about_info['emails']))
        print("📋 About 頁面合併後結果:")
        print(f"  - Emails: {info['emails']}")
        
    return info

def main():
    print("🚀 啟動 CloakBrowser...")
    try:
        context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW"
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)
        
    page = context.pages[0] if context.pages else context.new_page()
    
    try:
        extract_facebook_info(page, TARGET_URL)
    except Exception as e:
        print(f"❌ 執行出錯: {e}")
        
    context.close()

if __name__ == "__main__":
    main()
