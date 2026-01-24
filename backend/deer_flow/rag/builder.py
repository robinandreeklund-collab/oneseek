# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from backend.deer_flow.config.tools import SELECTED_RAG_PROVIDER, RAGProvider
from backend.deer_flow.rag.dify import DifyProvider
from backend.deer_flow.rag.moi import MOIProvider
from backend.deer_flow.rag.ragflow import RAGFlowProvider
from backend.deer_flow.rag.retriever import Retriever
from backend.deer_flow.rag.vikingdb_knowledge_base import VikingDBKnowledgeBaseProvider


def build_retriever() -> Retriever | None:
    if SELECTED_RAG_PROVIDER == RAGProvider.DIFY.value:
        return DifyProvider()
    if SELECTED_RAG_PROVIDER == RAGProvider.RAGFLOW.value:
        return RAGFlowProvider()
    elif SELECTED_RAG_PROVIDER == RAGProvider.MOI.value:
        return MOIProvider()
    elif SELECTED_RAG_PROVIDER == RAGProvider.VIKINGDB_KNOWLEDGE_BASE.value:
        return VikingDBKnowledgeBaseProvider()
    elif SELECTED_RAG_PROVIDER == RAGProvider.MILVUS.value:
        try:
            from backend.deer_flow.rag.milvus import MilvusProvider
            return MilvusProvider()
        except ImportError:
            raise ImportError("Milvus RAG provider selected but langchain_milvus not installed. Install with: pip install langchain-milvus pymilvus")
    elif SELECTED_RAG_PROVIDER == RAGProvider.QDRANT.value:
        try:
            from backend.deer_flow.rag.qdrant import QdrantProvider
            return QdrantProvider()
        except ImportError:
            raise ImportError("Qdrant RAG provider selected but langchain_qdrant not installed. Install with: pip install langchain-qdrant qdrant-client")
    elif SELECTED_RAG_PROVIDER:
        raise ValueError(f"Unsupported RAG provider: {SELECTED_RAG_PROVIDER}")
    return None
