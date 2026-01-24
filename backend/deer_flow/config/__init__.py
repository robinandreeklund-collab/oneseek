"""
Configuration management for DeerFlow integration

Adapted from DeerFlow's hybrid YAML + environment variable approach.
Original concept from: https://github.com/bytedance/deer-flow
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def load_env_config(prefix: str = "") -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Args:
        prefix: Optional prefix to filter environment variables
        
    Returns:
        Dictionary of configuration values
    """
    config = {}
    
    for key, value in os.environ.items():
        if prefix and not key.startswith(prefix):
            continue
        
        # Remove prefix if present
        config_key = key[len(prefix):] if prefix else key
        config[config_key.lower()] = value
    
    return config


def get_vllm_config() -> Dict[str, Any]:
    """
    Get VLLM-specific configuration.
    
    Returns:
        Dictionary with VLLM settings
    """
    return {
        "url": os.getenv("VLLM_URL", "http://localhost:8000/v1"),
        "model": os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ"),
        "temperature": float(os.getenv("VLLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("VLLM_MAX_TOKENS", "2048")),
    }


def get_vespa_config() -> Dict[str, Any]:
    """
    Get Vespa-specific configuration.
    
    Returns:
        Dictionary with Vespa settings
    """
    return {
        "url": os.getenv("VESPA_URL", ""),
        "cert_path": os.getenv("VESPA_CERT_PATH", ""),
        "key_path": os.getenv("VESPA_KEY_PATH", ""),
        "enabled": bool(os.getenv("VESPA_URL")),
    }


def get_search_config() -> Dict[str, Any]:
    """
    Get search tool configuration.
    
    Returns:
        Dictionary with search tool settings
    """
    return {
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
        "tavily_enabled": bool(os.getenv("TAVILY_API_KEY")),
        "duckduckgo_enabled": True,  # Always available
    }


def get_full_config() -> Dict[str, Any]:
    """
    Get complete configuration combining all sources.
    
    Returns:
        Dictionary with all configuration values
    """
    return {
        "vllm": get_vllm_config(),
        "vespa": get_vespa_config(),
        "search": get_search_config(),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
    }


def validate_config() -> tuple[bool, list[str]]:
    """
    Validate that required configuration is present.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    config = get_full_config()
    
    # VLLM is required
    if not config["vllm"]["url"]:
        errors.append("VLLM_URL is required")
    
    if not config["vllm"]["model"]:
        errors.append("VLLM_MODEL is required")
    
    # Search tools - at least one should be available
    search_config = config["search"]
    if not (search_config["tavily_enabled"] or search_config["duckduckgo_enabled"]):
        errors.append("At least one search tool must be configured")
    
    return (len(errors) == 0, errors)
