import sys
from unittest.mock import MagicMock

# Mock cloakbrowser before importing send_outreach
mock_cloak = MagicMock()
sys.modules['cloakbrowser'] = mock_cloak

import pytest
from unittest.mock import patch
import send_outreach

def test_backoff_and_circuit_breaker(monkeypatch):
    # Mock data loading to stay completely in memory
    monkeypatch.setattr(send_outreach, "load_data", lambda: None)
    monkeypatch.setattr(send_outreach, "save_data", lambda: None)
    monkeypatch.setattr(send_outreach, "log_outreach", lambda entry: None)
    
    send_outreach.csv_header = ['醫事機構名稱', 'Messenger', 'Personalized_Copy', 'Messenger_Status', 'Outreach_Time']
    send_outreach.csv_rows = [
        ['Clinic A', 'https://m.me/a', 'Copy A', '', ''],
        ['Clinic B', 'https://m.me/b', 'Copy B', '', ''],
        ['Clinic C', 'https://m.me/c', 'Copy C', '', ''],
        ['Clinic D', 'https://m.me/d', 'Copy D', '', ''],
    ]
    send_outreach.CSV_PATH = "dummy.csv"
    
    # Mock CloakBrowser launching to return a mock page/context
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    monkeypatch.setattr(send_outreach, "launch_persistent_context", lambda **kwargs: mock_context)
    
    # We will simulate:
    # 1. Success on Clinic A -> multiplier should stay 1.0, warning_count = 0
    # 2. Block on Clinic B -> warning_count = 1, multiplier = 2.0
    # 3. Block on Clinic C -> warning_count = 2, multiplier = 4.0
    # 4. Block on Clinic D -> warning_count = 3, multiplier = 8.0 -> should trigger sys.exit(1)
    
    call_idx = 0
    def mock_send(page, url, copy, dry_run=False):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 1:
            return True, "sent"
        else:
            return False, "delivery_failed"
            
    monkeypatch.setattr(send_outreach, "send_messenger_message", mock_send)
    
    # Mock time.sleep to run instantly
    monkeypatch.setattr(send_outreach.time, "sleep", lambda x: None)
    
    # Mock sys.argv to run with limit=4 and very short delays
    monkeypatch.setattr(sys, "argv", ["send_outreach.py", "--limit", "4", "--delay-min", "1", "--delay-max", "2"])
    
    # Executing send_outreach.main() should raise SystemExit with code 1
    with pytest.raises(SystemExit) as excinfo:
        send_outreach.main()
        
    assert excinfo.value.code == 1
    
    # Verify CSV rows state after run:
    # Clinic A: sent
    # Clinic B: backoff
    # Clinic C: backoff
    # Clinic D: session_halted
    assert send_outreach.csv_rows[0][3] == "sent"
    assert send_outreach.csv_rows[1][3] == "backoff"
    assert send_outreach.csv_rows[2][3] == "backoff"
    assert send_outreach.csv_rows[3][3] == "session_halted"

def test_backoff_recovery(monkeypatch):
    # Test that successful send recovers multiplier
    monkeypatch.setattr(send_outreach, "load_data", lambda: None)
    monkeypatch.setattr(send_outreach, "save_data", lambda: None)
    monkeypatch.setattr(send_outreach, "log_outreach", lambda entry: None)
    
    send_outreach.csv_header = ['醫事機構名稱', 'Messenger', 'Personalized_Copy', 'Messenger_Status', 'Outreach_Time']
    send_outreach.csv_rows = [
        ['Clinic A', 'https://m.me/a', 'Copy A', '', ''],
        ['Clinic B', 'https://m.me/b', 'Copy B', '', ''],
    ]
    send_outreach.CSV_PATH = "dummy.csv"
    
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    monkeypatch.setattr(send_outreach, "launch_persistent_context", lambda **kwargs: mock_context)
    
    def mock_send(page, url, copy, dry_run=False):
        return True, "sent"
            
    monkeypatch.setattr(send_outreach, "send_messenger_message", mock_send)
    monkeypatch.setattr(send_outreach.time, "sleep", lambda x: None)
    monkeypatch.setattr(sys, "argv", ["send_outreach.py", "--limit", "2", "--delay-min", "1", "--delay-max", "2"])
    
    # Should run to completion without raising SystemExit
    send_outreach.main()
    
    assert send_outreach.csv_rows[0][3] == "sent"
    assert send_outreach.csv_rows[1][3] == "sent"
