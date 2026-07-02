#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 資料庫管理模組 / SQLite Database Management Module
"""

import sqlite3
import csv
import os
from pathlib import Path

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
DB_PATH = str(WORKSPACE_DIR / "clinics.db")

def get_db_connection(db_path=DB_PATH):
    """
    建立與 SQLite 的連線並啟用 ROW 字典讀取格式。
    Establish a connection to SQLite and enable ROW dictionary mapping.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    """
    初始化 SQLite 資料表 / Initialize SQLite tables.
    """
    print(f"🗄️ 初始化資料庫 / Initializing database: {db_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 建立 clinics 資料表 / Create clinics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clinics (
        id TEXT PRIMARY KEY, -- 醫事機構代碼
        name TEXT NOT NULL,  -- 醫事機構名稱
        category TEXT,       -- 醫事機構種類
        phone TEXT,          -- 電話
        address TEXT,        -- 地址
        division TEXT,       -- 分區業務組
        contract_type TEXT,  -- 特約類別
        services TEXT,       -- 服務項目
        specialty TEXT,      -- 診療科別
        termination_date TEXT, -- 終止合約或歇業日期
        hours TEXT,          -- 固定看診時段
        notes TEXT,          -- 備註
        county_code TEXT,    -- 縣市別代碼
        start_date TEXT,     -- 合約起日
        fb_url TEXT,         -- FB_URL
        email TEXT,          -- Email
        messenger TEXT,      -- Messenger
        intro TEXT,          -- Intro
        latest_post TEXT,    -- Latest_Post
        personalized_copy TEXT, -- Personalized_Copy
        messenger_status TEXT, -- Messenger_Status
        outreach_time TEXT,  -- Outreach_Time
        ab_variant TEXT,     -- ab_variant (personalized / generic)
        website_url TEXT     -- Official Website URL
    )
    """)
    
    # 建立索引加快搜尋速度 / Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clinics_address ON clinics(address);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clinics_status ON clinics(messenger_status);")
    
    # 遷移：為舊的資料庫新增 website_url 欄位 / Migration: Add website_url to existing DB
    try:
        cursor.execute("ALTER TABLE clinics ADD COLUMN website_url TEXT;")
        conn.commit()
        print("  ℹ️ 遷移：已為 clinics 表新增 website_url 欄位 / Migrated: Added website_url to clinics table.")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    conn.commit()
    conn.close()
    print("  ✅ 資料庫初始化完成 / Database initialized successfully.")

def import_csv_to_db(csv_path, db_path=DB_PATH):
    """
    從 CSV 檔案匯入資料至 SQLite 資料庫。
    Import data from a CSV file into the SQLite database.
    """
    init_db(db_path)
    
    if not os.path.exists(csv_path):
        print(f"❌ 找不到 CSV 檔案 / CSV file not found: {csv_path}")
        return
        
    print(f"📥 開始匯入 CSV / Starting CSV import: {csv_path}")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 讀取 CSV / Read CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # 處理 UTF-8 BOM 導致的主鍵欄位名稱問題
        # Handle UTF-8 BOM causing primary key column name issues
        fieldnames = [name.lstrip('\ufeff') for name in reader.fieldnames]
        
        insert_count = 0
        update_count = 0
        
        for row in reader:
            # 整理資料列欄位名稱，移除 BOM / Normalize dictionary keys
            clean_row = {k.lstrip('\ufeff'): v for k, v in row.items()}
            
            # 主鍵 / Primary Key
            clinic_id = clean_row.get('醫事機構代碼', '').strip()
            if not clinic_id:
                continue
                
            # 檢查是否已存在 / Check if exists
            cursor.execute("SELECT id FROM clinics WHERE id = ?", (clinic_id,))
            exists = cursor.fetchone()
            
            # 欄位 mapping / Map columns
            data = (
                clean_row.get('醫事機構名稱', '').strip(),
                clean_row.get('醫事機構種類', '').strip(),
                clean_row.get('電話', '').strip(),
                clean_row.get('地址', '').strip(),
                clean_row.get('分區業務組', '').strip(),
                clean_row.get('特約類別', '').strip(),
                clean_row.get('服務項目', '').strip(),
                clean_row.get('診療科別', '').strip(),
                clean_row.get('終止合約或歇業日期', '').strip(),
                clean_row.get('固定看診時段', '').strip(),
                clean_row.get('備註', '').strip(),
                clean_row.get('縣市別代碼', '').strip(),
                clean_row.get('合約起日', '').strip(),
                clean_row.get('FB_URL', '').strip(),
                clean_row.get('Email', '').strip(),
                clean_row.get('Messenger', '').strip(),
                clean_row.get('Intro', '').strip(),
                clean_row.get('Latest_Post', '').strip(),
                clean_row.get('Personalized_Copy', '').strip(),
                clean_row.get('Messenger_Status', '').strip(),
                clean_row.get('Outreach_Time', '').strip(),
                clean_row.get('ab_variant', '').strip() or None
            )
            
            if exists:
                # 僅在 CSV 有新進度時更新 (保留原狀態) / Update existing (keep status if not in CSV)
                cursor.execute("""
                UPDATE clinics SET
                    name = ?, category = ?, phone = ?, address = ?, division = ?,
                    contract_type = ?, services = ?, specialty = ?, termination_date = ?,
                    hours = ?, notes = ?, county_code = ?, start_date = ?,
                    fb_url = COALESCE(NULLIF(fb_url, ''), ?),
                    email = COALESCE(NULLIF(email, ''), ?),
                    messenger = COALESCE(NULLIF(messenger, ''), ?),
                    intro = COALESCE(NULLIF(intro, ''), ?),
                    latest_post = COALESCE(NULLIF(latest_post, ''), ?),
                    personalized_copy = COALESCE(NULLIF(personalized_copy, ''), ?),
                    messenger_status = COALESCE(NULLIF(messenger_status, ''), ?),
                    outreach_time = COALESCE(NULLIF(outreach_time, ''), ?),
                    ab_variant = COALESCE(ab_variant, ?)
                WHERE id = ?
                """, data + (clinic_id,))
                update_count += 1
            else:
                # 插入新診所 / Insert new clinic
                cursor.execute("""
                INSERT INTO clinics (
                    id, name, category, phone, address, division, contract_type,
                    services, specialty, termination_date, hours, notes, county_code, start_date,
                    fb_url, email, messenger, intro, latest_post, personalized_copy,
                    messenger_status, outreach_time, ab_variant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (clinic_id,) + data)
                insert_count += 1
                
        conn.commit()
    conn.close()
    print(f"  🎉 匯入完成 / Import complete! 新增 / Inserted: {insert_count}, 更新 / Updated: {update_count}")

def get_city_candidates(city, limit=20, db_path=DB_PATH):
    """
    獲取指定城市且未發送的診所候選名單。
    Get unsent clinic candidates in a specific city.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 模糊比對縣市別名稱 / Match county/city name pattern
    city_pattern1 = f"%{city}%"
    city_pattern2 = f"%{city.replace('台', '臺')}%" if '台' in city else city_pattern1
    city_pattern3 = f"%{city.replace('臺', '台')}%" if '臺' in city else city_pattern1
    
    query = """
    SELECT * FROM clinics
    WHERE (address LIKE ? OR address LIKE ? OR address LIKE ?)
      AND (messenger_status IS NULL OR messenger_status NOT IN ('sent', 'dry_run'))
      -- 排除中醫與牙醫 / Exclude Traditional Chinese Medicine and Dentists
      AND name NOT LIKE '%中醫%' AND specialty NOT LIKE '%中醫%'
      AND name NOT LIKE '%牙醫%' AND name NOT LIKE '%牙科%' AND specialty NOT LIKE '%牙科%'
    LIMIT ?
    """
    
    cursor.execute(query, (city_pattern1, city_pattern2, city_pattern3, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_city_stats(city, db_path=DB_PATH):
    """
    獲取指定縣市的詳細行銷統計資訊。
    Get detailed marketing statistics for a specific city.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    city_pattern1 = f"%{city}%"
    city_pattern2 = f"%{city.replace('台', '臺')}%" if '台' in city else city_pattern1
    city_pattern3 = f"%{city.replace('臺', '台')}%" if '臺' in city else city_pattern1
    
    # 共用篩選條件 / Shared conditions
    where_clause = """
    WHERE (address LIKE ? OR address LIKE ? OR address LIKE ?)
      AND name NOT LIKE '%中醫%' AND specialty NOT LIKE '%中醫%'
      AND name NOT LIKE '%牙醫%' AND name NOT LIKE '%牙科%' AND specialty NOT LIKE '%牙科%'
    """
    
    stats = {}
    params = (city_pattern1, city_pattern2, city_pattern3)
    
    # 總診所數 / Total clinics
    cursor.execute(f"SELECT COUNT(*) FROM clinics {where_clause}", params)
    stats['total'] = cursor.fetchone()[0]
    
    # 已爬得 FB 專頁 / Has FB Page
    cursor.execute(f"SELECT COUNT(*) FROM clinics {where_clause} AND fb_url IS NOT NULL AND fb_url != '' AND fb_url != 'not_found'", params)
    stats['has_fb'] = cursor.fetchone()[0]
    
    # 有 Messenger 連結 / Has Messenger Link
    cursor.execute(f"SELECT COUNT(*) FROM clinics {where_clause} AND messenger LIKE 'http%'", params)
    stats['has_msg'] = cursor.fetchone()[0]
    
    # 有個人化文案 / Has Copy
    cursor.execute(f"SELECT COUNT(*) FROM clinics {where_clause} AND personalized_copy IS NOT NULL AND personalized_copy != ''", params)
    stats['has_copy'] = cursor.fetchone()[0]
    
    # 已成功發送 / Sent successfully
    cursor.execute(f"SELECT COUNT(*) FROM clinics {where_clause} AND messenger_status IN ('sent', 'dry_run')", params)
    stats['sent'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def update_clinic_fb(clinic_id, email, messenger, intro, latest_post, fb_url=None, db_path=DB_PATH):
    """
    更新診所爬取到的 Facebook 資訊。
    Update clinic's scraped Facebook info.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    if fb_url:
        cursor.execute("""
        UPDATE clinics SET
            email = ?, messenger = ?, intro = ?, latest_post = ?, fb_url = ?
        WHERE id = ?
        """, (email, messenger, intro, latest_post, fb_url, clinic_id))
    else:
        cursor.execute("""
        UPDATE clinics SET
            email = ?, messenger = ?, intro = ?, latest_post = ?
        WHERE id = ?
        """, (email, messenger, intro, latest_post, clinic_id))
        
    conn.commit()
    conn.close()

def update_clinic_fb_url(clinic_id, fb_url, db_path=DB_PATH):
    """
    更新診所 Facebook Page 網址。
    Update clinic's Facebook Page URL.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE clinics SET fb_url = ? WHERE id = ?", (fb_url, clinic_id))
    conn.commit()
    conn.close()

def update_clinic_copy(clinic_id, copy_text, ab_variant, db_path=DB_PATH):
    """
    更新診所生成的行銷文案與 A/B 測試組別。
    Update clinic's generated outreach copy and A/B variant.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE clinics SET
        personalized_copy = ?, ab_variant = ?
    WHERE id = ?
    """, (copy_text, ab_variant, clinic_id))
    conn.commit()
    conn.close()

def update_clinic_status(clinic_id, status, outreach_time, db_path=DB_PATH):
    """
    更新發送狀態與時間。
    Update messenger sending status and outreach timestamp.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE clinics SET
        messenger_status = ?, outreach_time = ?
    WHERE id = ?
    """, (status, outreach_time, clinic_id))
    conn.commit()
    conn.close()

def update_clinic_website(clinic_id, website_url, db_path=DB_PATH):
    """
    更新診所官方網站網址。
    Update clinic's official website URL.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE clinics SET website_url = ? WHERE id = ?", (website_url, clinic_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # 預設直接從本地 CSV 匯入測試 / Default CSV import test
    import_csv_to_db(str(WORKSPACE_DIR / "clinics西醫.csv"))
    print(get_city_stats("台中"))
