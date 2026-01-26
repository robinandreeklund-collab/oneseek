# Enable Thinking Feature Implementation

## Overview

This implementation adds support for Qwen3 model's built-in thinking functionality when deployed via vLLM. The feature allows users to toggle "deep thinking" mode via the "Djuptänkande" button in the frontend, and ensures that thinking output is always in Swedish when the Swedish locale is selected.

**⚠️ Important**: This feature **only works with Qwen3 models**. For other models (like Qwen2.5), the configuration is automatically skipped and models work normally without any impact.

## Key Changes

### 1. Frontend Changes

**File: `web/src/core/api/chat.ts`**

- Added Swedish locale mapping: `"sv": "sv-SE"` to the `LOCALE_MAP`
- This ensures the backend receives the correct locale format for Swedish users

### 2. Backend LLM Configuration

**File: `backend/deer_flow/llms/llm.py`**

#### New Function: `configure_llm_with_thinking()`

```python
def configure_llm_with_thinking(
    llm: BaseChatModel,
    enable_thinking: bool = False
) -> BaseChatModel
```

This function dynamically configures the LLM with the `enable_thinking` parameter:

- **Model Detection**: Checks if the model is Qwen3 before applying configuration
- **For Qwen3 models only**: Uses `extra_body` with `chat_template_kwargs: {"enable_thinking": true/false}`
- **For other models**: Returns LLM unchanged (no modification)
- **Binds parameters** to the LLM instance using `.bind()` method
- **Graceful fallback**: Returns original LLM if binding fails (catches TypeError and AttributeError)

#### Removed Hardcoded Configuration

- Removed hardcoded `enable_thinking` from Dashscope endpoint configuration
- This allows dynamic control based on user's button state

### 3. Backend Graph Node Updates

**File: `backend/deer_flow/graph/nodes.py`**

#### Planner Node Changes

1. **Import new function**: Added `configure_llm_with_thinking` to imports
2. **Dynamic thinking configuration**: 
   - When `enable_deep_thinking=True`: Configures LLM with `enable_thinking=True`
   - When `enable_deep_thinking=False`: Configures LLM with `enable_thinking=False`
3. **Swedish language enforcement**: 
   - When thinking mode is enabled AND locale is Swedish (sv-SE)
   - Adds a system message instructing the model to think in Swedish:
   
   ```
   VIKTIGT: När du tänker (i <think> taggar), MÅSTE du alltid tänka på SVENSKA.
   Alla dina tankar, resonemang och inre dialog ska vara på svenska.
   Detta är obligatoriskt och får inte ignoreras.
   ```

## How It Works

### User Flow

1. User clicks "Djuptänkande" button in the UI
2. Frontend sets `enable_deep_thinking: true` in the chat request
3. Backend receives the request with `enable_deep_thinking` parameter
4. Planner node:
   - Gets the reasoning LLM instance
   - Configures it with `enable_thinking=True` via vLLM API
   - If locale is Swedish, adds Swedish thinking instruction
5. LLM generates response with thinking tags in Swedish
6. Response is streamed back to the frontend

### Technical Details

#### vLLM API Parameters

The implementation uses vLLM's OpenAI-compatible API with custom parameters:

```python
# Correct binding method - pass extra_body as keyword argument
llm.bind(
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": True  # or False
        }
    }
)
```

**Important**: The `extra_body` parameter must be passed as a direct keyword argument to `.bind()`, not unpacked from a dictionary. This ensures vLLM receives the `chat_template_kwargs` correctly.

This parameter is passed to vLLM when the model is invoked, controlling whether Qwen3 generates `<think>...</think>` tags.

#### Locale Support

The implementation supports multiple locales:
- `en-US`: English (default)
- `zh-CN`: Chinese
- `sv-SE`: Swedish (newly added)

Swedish prompt templates already exist in `backend/deer_flow/prompts/*.sv_SE.md`, so the system automatically uses Swedish prompts when the locale is set to Swedish.

## Testing

### Manual Testing Steps

1. **Start vLLM server with Qwen3 model**:
   ```bash
   vllm serve Qwen/Qwen3-14B --port 8000
   ```

2. **Update conf.yaml**:
   ```yaml
   REASONING_MODEL:
     base_url: "http://localhost:8000/v1"
     model: "Qwen/Qwen3-14B"
     api_key: "EMPTY"
   ```

3. **Test with Djuptänkande OFF**:
   - Open OneSeek UI
   - Ensure "Djuptänkande" button is not highlighted
   - Send a query
   - Expected: Response without `<think>` tags

4. **Test with Djuptänkande ON (English)**:
   - Click "Djuptänkande" button (should highlight)
   - Send a query
   - Expected: Response with `<think>` tags containing reasoning

5. **Test with Djuptänkande ON (Swedish)**:
   - Switch UI to Swedish locale
   - Ensure "Djuptänkande" is enabled
   - Send a query
   - Expected: Response with `<think>` tags containing reasoning **in Swedish**

### Verification Points

- [ ] Button state correctly toggles `enable_deep_thinking` parameter
- [ ] vLLM receives correct `chat_template_kwargs` parameter
- [ ] Thinking mode is enabled/disabled as expected
- [ ] Swedish thinking instruction is added when locale is Swedish
- [ ] Thinking output is in Swedish when Swedish locale is used

## Configuration

### Requirements

- vLLM server running with **Qwen3 model** (not Qwen2.5 or earlier)
- Model must support the thinking mode feature
- Backend must be configured with the correct base_url pointing to vLLM

### Environment Variables

No new environment variables are required. The feature uses existing configuration:

- `REASONING_MODEL` in conf.yaml
- Frontend locale cookie (`NEXT_LOCALE`)

### Model Detection

The feature automatically detects if you're using a Qwen3 model by checking the `model_name` attribute. If the model name contains "qwen3" (case-insensitive), the thinking configuration is applied. Otherwise, the LLM is returned unchanged.

## Backwards Compatibility

The implementation maintains backwards compatibility:

1. **Non-Qwen3 models**: Configuration is automatically skipped - models work normally
2. **Qwen2.5 and earlier**: No impact - models function as before
3. **Existing functionality**: All existing LLM configurations continue to work
4. **Default behavior**: When `enable_deep_thinking=False`, models behave as before

## Known Limitations

1. **Model support**: **Only Qwen3 models** with thinking mode support benefit from this feature
2. **Qwen2.5**: Does not support thinking mode - feature is automatically disabled
3. **vLLM requirement**: The feature requires vLLM API with `chat_template_kwargs` support
4. **Language instruction**: While we add a Swedish instruction, the model's compliance depends on its training

## Future Enhancements

1. Add support for other reasoning models with similar features
2. Implement thinking mode for other nodes beyond planner
3. Add UI indicators showing when thinking mode is active in the response
4. Add configuration to customize the language instruction per locale

## References

- [vLLM Reasoning Outputs Documentation](https://docs.vllm.ai/en/latest/features/reasoning_outputs/)
- [Qwen3 Model Documentation](https://github.com/QwenLM/Qwen3)
- [LangChain BaseChatModel.bind() Documentation](https://python.langchain.com/docs/modules/model_io/chat/function_calling/)
