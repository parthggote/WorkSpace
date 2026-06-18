"""Background retrieval helpers that can be promoted to Celery tasks."""

from __future__ import annotations

from app.jobs.celery_app import celery_app
from app.services.reranker import AdvancedReranker, RetrievalCandidate


@celery_app.task(name="retrieval.rerank")
def rerank_candidates_task(
    query: str,
    candidates: list[dict[str, object]],
    top_k: int = 5,
) -> list[dict[str, object]]:
    typed_candidates = [
        RetrievalCandidate(
            id=str(candidate["id"]),
            text=str(candidate.get("text", "")),
            source_type=str(candidate.get("source_type", "message")),
            similarity=float(candidate.get("similarity", 0.0)),
            title=str(candidate["title"]) if candidate.get("title") else None,
            metadata=dict(candidate.get("metadata", {})),
        )
        for candidate in candidates
    ]
    ranked = AdvancedReranker().rerank(query, typed_candidates, top_k=top_k)
    return [
        {
            "id": candidate.id,
            "text": candidate.text,
            "source_type": candidate.source_type,
            "similarity": candidate.similarity,
            "title": candidate.title,
            "metadata": candidate.metadata,
            "rerank_score": candidate.rerank_score,
        }
        for candidate in ranked
    ]

