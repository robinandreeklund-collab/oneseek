# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from .builder import build_retriever
from .dify import DifyProvider
from .moi import MOIProvider
from .ragflow import RAGFlowProvider
from .retriever import Chunk, Document, Resource, Retriever
from .vikingdb_knowledge_base import VikingDBKnowledgeBaseProvider

# Optional RAG providers (imported conditionally to avoid dependency errors)
# from .milvus import MilvusProvider
# from .qdrant import QdrantProvider

__all__ = [
    "Retriever",
    "Document",
    "Resource",
    "DifyProvider",
    "RAGFlowProvider",
    "MOIProvider",
    # "MilvusProvider",  # Import conditionally in builder.py
    # "QdrantProvider",  # Import conditionally in builder.py
    "VikingDBKnowledgeBaseProvider",
    "Chunk",
    "build_retriever",
]
