import sys
from unittest.mock import MagicMock

# Mock cloakbrowser before importing run_campaign
mock_cloak = MagicMock()
sys.modules['cloakbrowser'] = mock_cloak

import pytest
from unittest.mock import patch, call
import run_campaign

def test_campaign_orchestrator_expired_session(monkeypatch):
    # Mock PROFILE_DIR existence
    monkeypatch.setattr(run_campaign, "PROFILE_DIR", MagicMock(exists=lambda: True))
    
    # Mock verify_facebook_session to return False (expired session)
    monkeypatch.setattr(run_campaign, "verify_facebook_session", lambda: False)
    monkeypatch.setattr(run_campaign, "release_browser_locks", lambda: None)
    
    # Run with default args
    monkeypatch.setattr(sys, "argv", ["run_campaign.py"])
    
    with pytest.raises(SystemExit) as excinfo:
        run_campaign.main()
    assert excinfo.value.code == 1

def test_campaign_orchestrator_success(monkeypatch):
    # Mock locks and session
    monkeypatch.setattr(run_campaign, "release_browser_locks", lambda: None)
    monkeypatch.setattr(run_campaign, "verify_facebook_session", lambda: True)
    
    # Mock subprocess.run to return a mock result with returncode=0
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(run_campaign.subprocess, "run", mock_run)
    
    # Patch argv to run limit 5, delay-min 200, delay-max 400
    monkeypatch.setattr(sys, "argv", [
        "run_campaign.py", 
        "--limit", "5", 
        "--delay-min", "200", 
        "--delay-max", "400"
    ])
    
    # Execute campaign
    run_campaign.main()
    
    # Let's inspect mock_run calls!
    # Expected sequence of calls:
    # 1. scrape_fb_info.py
    # 2. generate_copy_llm.py
    # 3. send_outreach.py --dry-run --limit 2
    # 4. send_outreach.py --limit 5 --delay-min 200 --delay-max 400
    
    called_args = [args[0][0] for args in mock_run.call_args_list]
    
    assert len(called_args) == 4
    
    # Verify first call: scrape_fb_info.py
    assert "scrape_fb_info.py" in called_args[0][1]
    
    # Verify second call: generate_copy_llm.py
    assert "generate_copy_llm.py" in called_args[1][1]
    
    # Verify third call: send_outreach.py --dry-run --limit 2
    assert "send_outreach.py" in called_args[2][1]
    assert "--dry-run" in called_args[2]
    assert "--limit" in called_args[2]
    assert "2" in called_args[2]
    
    # Verify fourth call: send_outreach.py --limit 5 --delay-min 200 --delay-max 400
    assert "send_outreach.py" in called_args[3][1]
    assert "--limit" in called_args[3]
    assert "5" in called_args[3]
    assert "--delay-min" in called_args[3]
    assert "200" in called_args[3]
    assert "--delay-max" in called_args[3]
    assert "400" in called_args[3]
    assert "--dry-run" not in called_args[3]

def test_campaign_orchestrator_dry_run_only(monkeypatch):
    monkeypatch.setattr(run_campaign, "release_browser_locks", lambda: None)
    monkeypatch.setattr(run_campaign, "verify_facebook_session", lambda: True)
    
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(run_campaign.subprocess, "run", mock_run)
    
    monkeypatch.setattr(sys, "argv", [
        "run_campaign.py", 
        "--dry-run-only", 
        "--limit", "10"
    ])
    
    run_campaign.main()
    
    called_args = [args[0][0] for args in mock_run.call_args_list]
    # Should only run 3 steps: scrape, copy, dry-run (no final campaign send)
    assert len(called_args) == 3
    assert "scrape_fb_info.py" in called_args[0][1]
    assert "generate_copy_llm.py" in called_args[1][1]
    assert "send_outreach.py" in called_args[2][1]
    assert "--dry-run" in called_args[2]

def test_campaign_orchestrator_skip_scrape(monkeypatch):
    monkeypatch.setattr(run_campaign, "release_browser_locks", lambda: None)
    monkeypatch.setattr(run_campaign, "verify_facebook_session", lambda: True)
    
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(run_campaign.subprocess, "run", mock_run)
    
    monkeypatch.setattr(sys, "argv", [
        "run_campaign.py", 
        "--skip-scrape", 
        "--dry-run-only"
    ])
    
    run_campaign.main()
    
    called_args = [args[0][0] for args in mock_run.call_args_list]
    # Should only run 2 steps: copy and dry-run (skips scrape and skips campaign send)
    assert len(called_args) == 2
    assert "generate_copy_llm.py" in called_args[0][1]
    assert "send_outreach.py" in called_args[1][1]
    assert "--dry-run" in called_args[1]
