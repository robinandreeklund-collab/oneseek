"""
LLM provider factory for OneSeek with VLLM support

Adapted from DeerFlow's LLM abstraction to support OneSeek's VLLM configuration.
Original concept from: https://github.com/bytedance/deer-flow
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
"""

import logging
import os
from typing import Any, Dict, Literal

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

LLMType = Literal["basic", "reasoning", "code", "vision"]

# Cache for LLM instances
_llm_cache: Dict[LLMType, BaseChatModel] = {}


def get_vllm_config() -> Dict[str, Any]:
    """
    Get VLLM configuration from environment variables.
    
    Returns:
        Dictionary with VLLM connection parameters
    """
    return {
        "base_url": os.getenv("VLLM_URL", "http://localhost:8000/v1"),
        "model": os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ"),
        "api_key": "EMPTY",  # VLLM doesn't require auth for local deployment
        "temperature": float(os.getenv("VLLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("VLLM_MAX_TOKENS", "2048")),
    }


def create_vllm_llm(llm_type: LLMType = "basic") -> BaseChatModel:
    """
    Create a ChatOpenAI instance configured for VLLM.
    
    VLLM exposes an OpenAI-compatible API, so we use ChatOpenAI with
    custom base_url pointing to the local VLLM server.
    
    Args:
        llm_type: Type of LLM to create (basic, reasoning, code, vision)
        
    Returns:
        Configured ChatOpenAI instance
    """
    config = get_vllm_config()
    
    # Add max_retries for robustness
    config["max_retries"] = 3
    
    # Adjust parameters based on LLM type
    if llm_type == "reasoning":
        # Reasoning models may benefit from lower temperature
        config["temperature"] = 0.3
    elif llm_type == "code":
        # Code generation benefits from deterministic output
        config["temperature"] = 0.1
    
    logger.info(f"Creating VLLM LLM of type '{llm_type}' with model: {config['model']}")
    
    return ChatOpenAI(**config)


def get_llm_by_type(llm_type: LLMType = "basic") -> BaseChatModel:
    """
    Get LLM instance by type. Returns cached instance if available.
    
    This follows DeerFlow's pattern of caching LLM instances to avoid
    repeated initialization overhead.
    
    Args:
        llm_type: Type of LLM to retrieve
        
    Returns:
        Cached or newly created LLM instance
    """
    if llm_type in _llm_cache:
        logger.debug(f"Returning cached LLM instance for type: {llm_type}")
        return _llm_cache[llm_type]
    
    llm = create_vllm_llm(llm_type)
    _llm_cache[llm_type] = llm
    return llm


def clear_llm_cache():
    """Clear the LLM instance cache."""
    global _llm_cache
    _llm_cache = {}
    logger.info("Cleared LLM cache")
