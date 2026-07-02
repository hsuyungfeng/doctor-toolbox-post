import sqlite3
import pytest
from pathlib import Path
import db

def test_database_migration_and_website_update(tmp_path):
    # Create a temporary database file
    db_file = tmp_path / "test_clinics.db"
    db_path = str(db_file)
    
    # Run database initialization on the temp file
    db.init_db(db_path)
    
    # Check that website_url column exists by connecting to the temp file
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(clinics)")
    columns = [col[1] for col in cursor.fetchall()]
    assert "website_url" in columns
    
    # Insert a dummy clinic
    cursor.execute("""
    INSERT INTO clinics (id, name, address) 
    VALUES ('test_01', 'Test Clinic', 'Test Address')
    """)
    conn.commit()
    conn.close()
    
    # Test update_clinic_website
    db.update_clinic_website('test_01', 'https://test-clinic.com', db_path=db_path)
    
    # Query back and verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT website_url FROM clinics WHERE id = 'test_01'")
    res = cursor.fetchone()
    assert res[0] == 'https://test-clinic.com'
    
    conn.close()
