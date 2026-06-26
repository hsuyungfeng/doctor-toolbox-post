import pytest
import json
from pydantic import ValidationError
from generate_copy_llm import ClinicCopySchema, generate_with_retry, GENERIC_COPY
import generate_copy_llm

def test_clinic_copy_schema_valid():
    # A valid Traditional Chinese copy
    valid_copy = "針對貴診所在小兒過敏與預防接種方面的專業特色，醫師工具箱能提供極大協助。我們的 AI 語音病歷系統能即時轉錄看診對話，自動生成符合小兒發展與疫苗紀錄的 SOAP 病歷，免去繁瑣的手動輸入。讓您可以更專注於與家長的溝通。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator"
    schema = ClinicCopySchema(personalized_copy=valid_copy, specialty_tag="小兒科")
    assert schema.personalized_copy == valid_copy
    assert schema.specialty_tag == "小兒科"

def test_clinic_copy_schema_invalid_length():
    # Too short
    short_copy = "很短的文案。"
    with pytest.raises(ValidationError) as excinfo:
        ClinicCopySchema(personalized_copy=short_copy, specialty_tag="眼科")
    assert "長度" in str(excinfo.value)

    # Too long
    long_copy = "針對貴診所在眼科領域的卓越成就，我們特別推出全新升級版醫師工具箱系統。本系統結合了先進的即時語音轉錄功能與高度客製化的 SOAP 範本設計，專為忙碌的眼科醫師打造，能夠精準記錄每位患者的視力檢查、眼底鏡檢查及後續治療計畫，並完美對接現有 HIS 診所系統，徹底改善您的病歷書寫體驗，從此省下 80% 時間。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator。此外，本系統還提供 LINE OA 預約及自動問答功能，協助提升診所管理效率與患者滿意度，為您的診所增添更多核心競爭力。"
    with pytest.raises(ValidationError) as excinfo:
        ClinicCopySchema(personalized_copy=long_copy, specialty_tag="眼科")
    assert "長度" in str(excinfo.value)

def test_clinic_copy_schema_simplified_chinese():
    # Contains simplified Chinese "极"
    simplified_copy_1 = "針對貴診所在小兒過敏與預防接種方面的專業特色，醫師工具箱能提供极大協助。我們的 AI 語音病歷系統能即時轉錄看診對話，自動生成符合小兒發展與疫苗紀錄的 SOAP 病歷，免去繁瑣的手動輸入。讓您可以更專注於與家長的溝通。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator"
    with pytest.raises(ValidationError) as excinfo:
        ClinicCopySchema(personalized_copy=simplified_copy_1, specialty_tag="小兒科")
    assert "簡體字" in str(excinfo.value)

def test_clinic_copy_schema_blacklist():
    # Contains "最佳"
    blacklist_copy = "針對貴診所在眼科領域的特色，醫師工具箱是全台第一且最佳的 AI 語音病歷記載工具，保證療效好並能根治打字痛苦。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator"
    with pytest.raises(ValidationError) as excinfo:
        ClinicCopySchema(personalized_copy=blacklist_copy, specialty_tag="眼科")
    assert "違反醫療法禁用詞" in str(excinfo.value)

def test_generate_with_retry_success(monkeypatch):
    # Mock call_local_llm to return a valid JSON string
    valid_json = json.dumps({
        "personalized_copy": "針對貴診所在小兒過敏與預防接種方面的專業特色，醫師工具箱能提供極大協助。我們的 AI 語音病歷系統能即時轉錄看診對話，自動生成符合小兒發展與疫苗紀錄的 SOAP 病歷。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator",
        "specialty_tag": "小兒科"
    })
    monkeypatch.setattr(generate_copy_llm, "call_local_llm", lambda prompt: valid_json)
    
    result = generate_with_retry("榮光診所", "小兒科", "簡介", "貼文")
    assert "小兒過敏" in result
    assert result != GENERIC_COPY

def test_generate_with_retry_fallback_after_failures(monkeypatch):
    # Mock call_local_llm to return invalid responses
    invalid_json = json.dumps({
        "personalized_copy": "太短了",
        "specialty_tag": "眼科"
    })
    
    call_count = 0
    def mock_call(prompt):
        nonlocal call_count
        call_count += 1
        return invalid_json
        
    monkeypatch.setattr(generate_copy_llm, "call_local_llm", mock_call)
    
    # We should get the fallback copy
    result = generate_with_retry("榮光診所", "小兒科", "簡介", "貼文", retries=2)
    assert result == GENERIC_COPY
    # Verify it retried 3 times (1 initial + 2 retries)
    assert call_count == 3
