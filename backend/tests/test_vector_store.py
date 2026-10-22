"""Tests for Gemini Embedding Vector Store & NumPy Cosine Similarity.

Validates:
1. VectorStore generates embeddings offline and online.
2. Cosine similarity accurately calculated using NumPy.
3. Vector records persisted to SQLite memories table.
4. Top-K semantic nearest neighbor retrieval.
"""

import pytest
import numpy as np
from backend.app.memory.vector_store import VectorStore, cosine_similarity


def test_cosine_similarity_numpy():
    """Verify NumPy cosine similarity implementation."""
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    # Identical vectors
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0
    # Orthogonal vectors
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0

    # Zero vector handling
    v_zero = np.zeros(3, dtype=np.float32)
    assert cosine_similarity(v1, v_zero) == 0.0


def test_vector_store_embedding_generation():
    """Verify embedding generation produces non-zero normalized vectors."""
    store = VectorStore()
    vec1 = store.get_embedding("Vehicle speed threshold error at 80 km/h")
    vec2 = store.get_embedding("Timeout message lost door unlocked")

    assert len(vec1) == store.dim
    assert len(vec2) == store.dim
    # Norm must be ~1.0 (unit vector)
    assert pytest.approx(np.linalg.norm(vec1), 0.01) == 1.0
    assert pytest.approx(np.linalg.norm(vec2), 0.01) == 1.0


def test_vector_store_sqlite_add_and_search():
    """Verify vector store persistence in SQLite and semantic cosine retrieval."""
    store = VectorStore()
    
    # Store memory entries
    id1 = store.add_memory(
        key="bug:threshold_80",
        content="ECU threshold set to 80 km/h instead of 20 km/h causing door unlock failure.",
        memory_type="failure_fix",
        metadata={"cause": "threshold_misconfiguration", "fix": "set_to_20"},
    )
    assert id1 > 0

    id2 = store.add_memory(
        key="bug:timeout_lost_frame",
        content="ECU ignores lost CAN frame on speed timeout leaving doors unlocked.",
        memory_type="failure_fix",
        metadata={"cause": "missing_failsafe", "fix": "lock_on_lost"},
    )
    assert id2 > 0

    # Search with a query semantically aligned with threshold bug
    results_threshold = store.search(
        query="speed 80 threshold failure unlocked",
        memory_type="failure_fix",
        top_k=2,
    )
    assert len(results_threshold) >= 1
    top_match = results_threshold[0]
    assert "threshold" in top_match["key"] or "threshold" in top_match["content"]
    assert top_match["similarity"] > 0.3

    # Search with a query semantically aligned with timeout bug
    results_timeout = store.search(
        query="timeout lost CAN frame failsafe",
        memory_type="failure_fix",
        top_k=2,
    )
    assert len(results_timeout) >= 1
    top_timeout = results_timeout[0]
    assert "timeout" in top_timeout["key"] or "lost" in top_timeout["content"]
    assert top_timeout["similarity"] > 0.3
