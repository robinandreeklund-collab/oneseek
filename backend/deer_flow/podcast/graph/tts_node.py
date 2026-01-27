# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
import logging
import os

from backend.deer_flow.podcast.graph.state import PodcastState
from backend.deer_flow.tools.tts import OpenAITTS

logger = logging.getLogger(__name__)


def tts_node(state: PodcastState):
    logger.info("Generating audio chunks for podcast...")
    tts_client = _create_tts_client()
    for line in state["script"].lines:
        # Map male to 'onyx' and female to 'nova'
        tts_client.voice = (
            "onyx" if line.speaker == "male" else "nova"
        )
        result = tts_client.text_to_speech(line.paragraph, speed_ratio=1.05)
        if result["success"]:
            audio_data = result["audio_data"]
            audio_chunk = base64.b64decode(audio_data)
            state["audio_chunks"].append(audio_chunk)
        else:
            logger.error(result["error"])
    return {
        "audio_chunks": state["audio_chunks"],
    }


def _create_tts_client():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise Exception("OPENAI_API_KEY is not set")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")
    model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    return OpenAITTS(
        api_key=api_key,
        voice=voice,
        model=model,
    )
