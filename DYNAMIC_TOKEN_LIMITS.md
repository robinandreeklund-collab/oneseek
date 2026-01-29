# Dynamic Token Limit Support

## Problem

The debate mode had hardcoded token limits based on a 95K context window:
- Max context: 60,000 tokens (hardcoded)
- Warning threshold: 30,000 tokens
- Critical threshold: 50,000 tokens

However, users can run different models with different context windows:
- **User's VLLM**: 128K tokens
- Doubao/Claude: 200K tokens  
- GPT-4: 120K tokens
- Gemini: 180K tokens

The hardcoded limits wasted available context and showed misleading error messages.

## Solution

### Dynamic Token Limit Detection

The `DebateFlow` now automatically detects the actual token limit from LLM configuration:

```python
from backend.deer_flow.llms.llm import get_llm_token_limit_by_type

self.token_limit = get_llm_token_limit_by_type("basic")  # Gets actual limit
self.max_context_tokens = int(self.token_limit * 0.6)    # 60% for input
```

### Adaptive Safety Margins

All limits are now calculated dynamically:

1. **Max Context**: 60% of total token limit (leaving 40% for response)
2. **Warning Threshold**: 50% of max context
3. **Critical Threshold**: 83% of max context

### Benefits

**For 128K Model (User's VLLM):**
- Old limit: 60,000 tokens
- New limit: 76,800 tokens
- **Gained: +16,800 tokens (28% more context!)**

**For 200K Model (Doubao/Claude):**
- Old limit: 60,000 tokens  
- New limit: 120,000 tokens
- **Gained: +60,000 tokens (100% more context!)**

## Examples

### Before (Hardcoded)
```
Max context: 60,000 tokens (always)
Error: "Context (65,000 tokens) exceeds 60K limit. Safety margin for 95K model."
```

### After (Dynamic)
```
128K model detected
Max context: 76,800 tokens (60% of 128K)
Error: "Context (80,000 tokens) exceeds 76,800 limit. Safety margin for 128000 token model."
```

## Configuration

Token limits are read from LLM configuration in priority order:

1. **Explicit config**: `token_limit` in `conf.yaml`
2. **Model name inference**: Detected from model name patterns
3. **Safe default**: 100,000 tokens

Example config:
```yaml
basic_model:
  model: "your-model-name"
  token_limit: 128000  # Optional: explicit limit
```

If not configured, the system infers from model name automatically.

## Testing

Run the test to verify calculations:
```bash
python backend/test_dynamic_token_limits.py
```

Output:
```
✓ 128K model (user's VLLM):
  Total limit: 128,000 tokens
  Max context: 76,800 tokens (60%)
  Reserved for response: 51,200 tokens (40%)

✅ Gained 16,800 tokens of usable context!
```

## Impact

- ✅ No more wasted context space
- ✅ Accurate error messages with actual limits
- ✅ Automatic adaptation to any model size
- ✅ Better utilization of large context models
- ✅ Same code works for 95K, 128K, 200K+ models

## Files Changed

1. `backend/debate_flow.py`:
   - Added dynamic token limit detection in `__init__`
   - Calculated `max_context_tokens` dynamically (60% of total)
   - Updated all hardcoded 60000 references to use `self.max_context_tokens`
   - Updated warning/critical thresholds to be dynamic
   - Removed all "95K model" comments

2. `backend/test_dynamic_token_limits.py` (NEW):
   - Comprehensive tests for dynamic limit calculations
   - Comparison of old vs new limits
   - Validation of threshold ordering
