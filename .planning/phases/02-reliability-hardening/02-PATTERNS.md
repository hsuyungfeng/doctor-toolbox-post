# Phase 2: Reliability Hardening — Patterns

> Generated to map existing code patterns and reference files. Consumed by the planner.

---

## Files to Modify

| Target File | Analog File | Pattern / Purpose |
|-------------|-------------|-------------------|
| `generate_copy_llm.py` | `generate_copy_llm.py` (self) | **Pydantic Validation & Retry Loop:** Integrate `pydantic` validation to verify model responses. If validation fails, retry up to 2 times, and then fall back to `generic_copy` on exhaustion. |
| `send_outreach.py` | `send_outreach.py` (self) | **Adaptive Delay Backoff & Circuit Breaker:** Keep track of rate limit soft warning messages and dynamically double delay intervals. Implement a session-level threshold check to alert and halt on persistent blocks. |

---

## Code Excerpts & Patterns

### 1. Pydantic Model Integration
To ensure the LLM output conforms to regulatory requirements and length limits, define the schema in `generate_copy_llm.py`:

```python
from pydantic import BaseModel, Field, field_validator

class ClinicOutreachCopy(BaseModel):
    personalized_copy: str = Field(description="Traditional Chinese outreach message, 100-150 characters.")

    @field_validator("personalized_copy")
    @classmethod
    def validate_content(cls, v: str) -> str:
        # Check length
        if len(v) < 80 or len(v) > 180:
            raise ValueError("Character length must be between 80 and 180 characters.")
        # Check simplified Chinese characters
        simplified = ["亲", "医", "这", "国"]
        if any(char in v for char in simplified):
            raise ValueError("Simplified Chinese character leakage detected.")
        # Check superlative blacklist (Taiwan Medical Care Act)
        blacklist = ["最佳", "最先進", "保證療效", "根治", "全台第一"]
        for term in blacklist:
            if term in v:
                raise ValueError(f"Prohibited superlative term found: '{term}'")
        return v
```

### 2. Adaptive Backoff Delay Pattern
In `send_outreach.py`, track the delay multiplier state:

```python
# Track delay scaling factor
delay_multiplier = 1.0

# When rate limit signal is detected on screen:
if "無法傳送" in page_source or "暫時限制" in page_source:
    print("⚠️ Detected soft warning signal on Facebook. Increasing backoff delay multiplier.")
    delay_multiplier *= 2.0
    # Increase delay bounds for the next sleep iteration:
    sleep_time = random.uniform(300 * delay_multiplier, 600 * delay_multiplier)
```

### 3. Circuit Breaker / Hard Halt Pattern
To prevent permanent account ban, hard exit the process if blocks are persistent:

```python
warning_count = 0
MAX_WARNINGS = 3

# Inside sending loop:
if block_detected:
    warning_count += 1
    if warning_count >= MAX_WARNINGS:
        print("❌ Session block count exceeded threshold. Halting campaign immediately!")
        sys.exit(1)
```
