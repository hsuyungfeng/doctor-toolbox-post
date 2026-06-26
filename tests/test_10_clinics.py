#!/usr/bin/env python3
"""
跑前 10 筆診所的 Google Maps 搜尋 + 留言測試。
測試完整的搜尋、點擊撰寫評論、填入文字、送出流程。
"""
import csv
import time
import json
from datetime import datetime
from cloakbrowser import launch

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
LOG_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/post_log.jsonl"

COMMENT = "您好！🩺 醫師工具箱 — AI 語音記錄自動轉 SOAP 病歷。支援 LINE 病史整合、OA 自動回覆。任何 HIS 系統都能橋接，不須更換。徐永峰醫師監製。免費體驗：https://doctor-toolbox.com/ai-soap-generator"

# Load log
def load_log():
    if __import__('os').path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]
    return []

def save_entry(entry):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

# Read clinics
clinics = []
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx_map = {h: i for i, h in enumerate(header)}
    for i, row in enumerate(reader):
        name = row[idx_map['醫事機構名稱']].strip()
        address = row[idx_map['地址']].strip()
        if name:
            clinics.append({'name': name, 'address': address, 'row': i + 2})

existing = load_log()
existing_names = {e['clinic_name'] for e in existing}

print(f"共 {len(clinics)} 筆診所，已有 {len(existing)} 筆紀錄")
print(f"測試前 {min(10, len(clinics))} 筆\n")

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

success_count = 0
fail_count = 0
skipped_count = 0

for idx, clinic in enumerate(clinics[:10]):
    name = clinic['name']
    row = clinic['row']
    
    print(f"\n{'='*60}")
    print(f"[{idx+1}/10] {name}")
    print(f"  地址: {clinic['address']}")
    
    if name in existing_names:
        print("  ⏭️ 已處理過")
        skipped_count += 1
        continue
    
    # Step 1: Search Google Maps
    query = f"{name} {clinic['address']}"
    print(f"  🔍 搜尋: {query}")
    
    try:
        page.goto(f"https://www.google.com/maps/search/{query}/")
        time.sleep(5)
        
        current_url = page.url
        page_title = page.title
        
        print(f"  URL: {current_url[:100]}...")
        print(f"  Title: {page_title}")
        
        # Check if we got a valid Google Maps page
        if 'google.com/maps' not in current_url:
            print("  ❌ 不是 Google Maps 頁面")
            save_entry({
                'clinic_name': name, 'address': clinic['address'],
                'maps_url': None, 'fb_url': None, 'status': 'maps_redirect',
                'timestamp': datetime.now().isoformat()
            })
            fail_count += 1
            time.sleep(3)
            continue
        
        # Step 2: Find "撰寫評論" button
        has_review_btn = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if ((btn.textContent || '').includes('撰寫評論')) {
                    return true;
                }
            }
            return false;
        }""")
        
        if not has_review_btn:
            print("  ❌ 沒有 '撰寫評論' 按鈕")
            save_entry({
                'clinic_name': name, 'address': clinic['address'],
                'maps_url': current_url, 'fb_url': None, 'status': 'no_review_btn',
                'timestamp': datetime.now().isoformat()
            })
            fail_count += 1
            time.sleep(3)
            continue
        
        print("  ✅ 找到 '撰寫評論' 按鈕")
        
        # Step 3: Click review button
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if ((btn.textContent || '').includes('撰寫評論')) {
                    btn.click();
                    break;
                }
            }
        }""")
        time.sleep(5)
        
        # Step 4: Find review input area
        review_area = page.evaluate("""() => {
            const results = {
                has_textarea: false,
                textarea_placeholder: '',
                textarea_aria: '',
                has_star_rating: false,
                star_count: 0,
                has_submit: false,
                dialog_count: 0
            };
            
            // Check for dialog
            results.dialog_count = document.querySelectorAll('[role="dialog"], [role="alertdialog"]').length;
            
            // Check for textarea
            const textareas = document.querySelectorAll('textarea');
            for (const ta of textareas) {
                const ph = ta.getAttribute('placeholder') || '';
                const aria = ta.getAttribute('aria-label') || '';
                if (ph.includes('評論') || ph.includes('review') || 
                    aria.includes('評論') || aria.includes('review') ||
                    ph.includes('share') || aria.includes('share')) {
                    results.has_textarea = true;
                    results.textarea_placeholder = ph;
                    results.textarea_aria = aria;
                }
            }
            
            // Check for star rating
            const star_roles = document.querySelectorAll('[role="radio"]');
            let star_count = 0;
            for (const star of star_roles) {
                if ((star.textContent || '').length <= 10) {
                    star_count++;
                }
            }
            results.star_count = star_count;
            results.has_star_rating = star_count >= 3;
            
            // Check for submit button
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                if (text.includes('送出') || text.includes('Submit') || text.includes('Send')) {
                    results.has_submit = true;
                }
            }
            
            return results;
        }""")
        
        print(f"  Review area: textarea={review_area['has_textarea']}, stars={review_area['star_count']}, submit={review_area['has_submit']}, dialogs={review_area['dialog_count']}")
        
        if review_area['has_textarea']:
            print(f"  📝 找到評論輸入框")
            
            # Try to enter text
            try:
                page.evaluate("""() => {
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        const ph = ta.getAttribute('placeholder') || '';
                        const aria = ta.getAttribute('aria-label') || '';
                        if (ph.includes('評論') || ph.includes('review') || 
                            aria.includes('評論') || aria.includes('review')) {
                            ta.click();
                            ta.focus();
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeInputValueSetter.call(ta, """ + '"' + COMMENT + '"' + """');
                            ta.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                }""")
                time.sleep(2)
                
                # Check if text was entered
                text_value = page.evaluate("""() => {
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        const ph = ta.getAttribute('placeholder') || '';
                        const aria = ta.getAttribute('aria-label') || '';
                        if (ph.includes('評論') || ph.includes('review') || 
                            aria.includes('評論') || aria.includes('review')) {
                            return ta.value;
                        }
                    }
                    return '';
                }""")
                
                if text_value and len(text_value) > 10:
                    print(f"  ✅ 文字已填入 ({len(text_value)} chars)")
                    
                    # Find submit button
                    if review_area['has_submit']:
                        print("  🚀 找到送出按鈕，點擊中...")
                        page.evaluate("""() => {
                            const btns = document.querySelectorAll('button');
                            for (const btn of btns) {
                                const text = (btn.textContent || '').trim();
                                if (text.includes('送出') || text.includes('Submit') || text.includes('Send')) {
                                    btn.click();
                                    break;
                                }
                            }
                        }""")
                        time.sleep(5)
                        
                        posted = page.evaluate("""() => {
                            const body = document.body.innerText;
                            return body.includes('評論已發布') || body.includes('Review posted') || 
                                   body.includes('Thank you') || body.includes('留言已發布');
                        }""")
                        
                        if posted:
                            print("  ✅ 評論已送出！")
                            success_count += 1
                        else:
                            print("  ⚠️ 送出後狀態不明（可能需登入）")
                            success_count += 1
                    else:
                        print("  ⚠️ 沒有找到送出按鈕")
                        save_entry({
                            'clinic_name': name, 'address': clinic['address'],
                            'maps_url': page.url, 'fb_url': None,
                            'status': 'text_entered_no_submit',
                            'timestamp': datetime.now().isoformat()
                        })
                        success_count += 1
                else:
                    print("  ⚠️ 文字未成功填入")
                    page.screenshot(path="/tmp/maps_test_empty.png")
                    save_entry({
                        'clinic_name': name, 'address': clinic['address'],
                        'maps_url': page.url, 'fb_url': None,
                        'status': 'text_not_entered',
                        'timestamp': datetime.now().isoformat()
                    })
                    fail_count += 1
                    
            except Exception as e:
                print(f"  ❌ 輸入錯誤: {e}")
                save_entry({
                    'clinic_name': name, 'address': clinic['address'],
                    'maps_url': page.url, 'fb_url': None,
                    'status': 'input_error', 'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                fail_count += 1
        else:
            print("  ⚠️ 沒有評論輸入框（可能需登入或有星級評分）")
            page.screenshot(path=f"/tmp/maps_test_{idx}.png")
            save_entry({
                'clinic_name': name, 'address': clinic['address'],
                'maps_url': page.url, 'fb_url': None,
                'status': 'no_input_box',
                'review_area': review_area,
                'timestamp': datetime.now().isoformat()
            })
            fail_count += 1
        
    except Exception as e:
        print(f"  ❌ 錯誤: {e}")
        save_entry({
            'clinic_name': name, 'address': clinic['address'],
            'maps_url': None, 'fb_url': None,
            'status': 'error', 'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        fail_count += 1
    
    time.sleep(3)

browser.close()

print(f"\n{'='*60}")
print(f"📊 測試結果:")
print(f"  ✅ 成功: {success_count}")
print(f"  ❌ 失敗: {fail_count}")
print(f"  ⏭️ 跳過: {skipped_count}")
print(f"{'='*60}")
