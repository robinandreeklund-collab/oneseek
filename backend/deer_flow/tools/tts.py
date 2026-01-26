# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Text-to-Speech module using OpenAI TTS API.
"""

import base64
import json
import logging
import uuid
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class VolcengineTTS:
    """
    Client for volcengine Text-to-Speech API.
    """

    def __init__(
        self,
        appid: str,
        access_token: str,
        cluster: str = "volcano_tts",
        voice_type: str = "BV700_V2_streaming",
        host: str = "openspeech.bytedance.com",
    ):
        """
        Initialize the volcengine TTS client.

        Args:
            appid: Platform application ID
            access_token: Access token for authentication
            cluster: TTS cluster name
            voice_type: Voice type to use
            host: API host
        """
        self.appid = appid
        self.access_token = access_token
        self.cluster = cluster
        self.voice_type = voice_type
        self.host = host
        self.api_url = f"https://{host}/api/v1/tts"
        self.header = {"Authorization": f"Bearer;{access_token}"}

    def text_to_speech(
        self,
        text: str,
        encoding: str = "mp3",
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
        text_type: str = "plain",
        with_frontend: int = 1,
        frontend_type: str = "unitTson",
        uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert text to speech using volcengine TTS API.

        Args:
            text: Text to convert to speech
            encoding: Audio encoding format
            speed_ratio: Speech speed ratio
            volume_ratio: Speech volume ratio
            pitch_ratio: Speech pitch ratio
            text_type: Text type (plain or ssml)
            with_frontend: Whether to use frontend processing
            frontend_type: Frontend type
            uid: User ID (generated if not provided)

        Returns:
            Dictionary containing the API response and base64-encoded audio data
        """
        if not uid:
            uid = str(uuid.uuid4())

        request_json = {
            "app": {
                "appid": self.appid,
                "token": self.access_token,
                "cluster": self.cluster,
            },
            "user": {"uid": uid},
            "audio": {
                "voice_type": self.voice_type,
                "encoding": encoding,
                "speed_ratio": speed_ratio,
                "volume_ratio": volume_ratio,
                "pitch_ratio": pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": text_type,
                "operation": "query",
                "with_frontend": with_frontend,
                "frontend_type": frontend_type,
            },
        }

        try:
            sanitized_text = text.replace("\r\n", "").replace("\n", "")
            logger.debug(f"Sending TTS request for text: {sanitized_text[:50]}...")
            response = requests.post(
                self.api_url, json.dumps(request_json), headers=self.header
            )
            response_json = response.json()

            if response.status_code != 200:
                logger.error(f"TTS API error: {response_json}")
                return {"success": False, "error": response_json, "audio_data": None}

            if "data" not in response_json:
                logger.error(f"TTS API returned no data: {response_json}")
                return {
                    "success": False,
                    "error": "No audio data returned",
                    "audio_data": None,
                }

            return {
                "success": True,
                "response": response_json,
                "audio_data": response_json["data"],  # Base64 encoded audio data
            }

        except Exception as e:
            logger.exception(f"Error in TTS API call: {str(e)}")
            return {"success": False, "error": "TTS API call error", "audio_data": None}


class OpenAITTS:
    """
    Client for OpenAI Text-to-Speech API (NoteGPT).
    """

    def __init__(
        self,
        api_key: str,
        voice: str = "alloy",
        model: str = "tts-1",
    ):
        """
        Initialize the OpenAI TTS client.

        Args:
            api_key: OpenAI API key for authentication
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: Model to use (tts-1 or tts-1-hd)
        """
        self.api_key = api_key
        self.voice = voice
        self.model = model
        self.api_url = "https://api.openai.com/v1/audio/speech"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def text_to_speech(
        self,
        text: str,
        encoding: str = "mp3",
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
        text_type: str = "plain",
        with_frontend: int = 1,
        frontend_type: str = "unitTson",
        uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert text to speech using OpenAI TTS API.

        Args:
            text: Text to convert to speech
            encoding: Audio encoding format (mp3, opus, aac, flac)
            speed_ratio: Speech speed ratio (0.25 to 4.0)
            volume_ratio: Speech volume ratio (not supported by OpenAI, ignored)
            pitch_ratio: Speech pitch ratio (not supported by OpenAI, ignored)
            text_type: Text type (plain or ssml, ignored)
            with_frontend: Whether to use frontend processing (ignored)
            frontend_type: Frontend type (ignored)
            uid: User ID (ignored)

        Returns:
            Dictionary containing the API response and base64-encoded audio data
        """
        # Map encoding to OpenAI format
        format_map = {
            "mp3": "mp3",
            "opus": "opus",
            "aac": "aac",
            "flac": "flac",
        }
        response_format = format_map.get(encoding.lower(), "mp3")

        # Clamp speed to OpenAI's acceptable range
        speed = max(0.25, min(4.0, speed_ratio))

        request_data = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": response_format,
            "speed": speed,
        }

        try:
            text_preview = text.replace("\r\n", "").replace("\n", "")
            logger.debug(f"Sending OpenAI TTS request for text: {text_preview[:50]}...")
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=request_data,
            )

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except (ValueError, KeyError):
                    pass
                logger.error(f"OpenAI TTS API error: {error_msg}")
                return {"success": False, "error": error_msg, "audio_data": None}

            # OpenAI returns raw audio bytes, encode to base64 for consistency
            audio_bytes = response.content
            audio_data = base64.b64encode(audio_bytes).decode("utf-8")

            return {
                "success": True,
                "response": {"status": "success"},
                "audio_data": audio_data,  # Base64 encoded audio data
            }

        except Exception as e:
            logger.exception(f"Error in OpenAI TTS API call: {str(e)}")
            return {"success": False, "error": "TTS API call error", "audio_data": None}
