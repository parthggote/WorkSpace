"""Advanced deterministic reranking for memory, web, and document retrieval."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Iterable


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-]*", re.IGNORECASE)
SOURCE_TYPE_BOOSTS = {
    "summary": 0.08,
    "document": 0.06,
    "web": 0.08,
    "message": 0.02,
}


@dataclass(frozen=True)
class RetrievalCandidate:
    id: str
    text: str
    source_type: str
    similarity: float = 0.0
    created_at: datetime | None = None
    title: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    rerank_score: float = 0.0


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def lexical_overlap(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    text_tokens = tokenize(text)
    return len(query_tokens & text_tokens) / len(query_tokens)


def recency_score(created_at: datetime | None, *, half_life_days: int = 30) -> float:
    if created_at is None:
        return 0.0
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - created_at).total_seconds() / 86400)
    return math.exp(-age_days / max(1, half_life_days))


class AdvancedReranker:
    """Rank candidates while preserving workspace filtering done upstream."""

    def __init__(
        self,
        *,
        similarity_weight: float = 0.58,
        lexical_weight: float = 0.22,
        recency_weight: float = 0.10,
        title_weight: float = 0.10,
        diversity_penalty: float = 0.08,
        minimum_score: float = 0.0,
    ) -> None:
        self.similarity_weight = similarity_weight
        self.lexical_weight = lexical_weight
        self.recency_weight = recency_weight
        self.title_weight = title_weight
        self.diversity_penalty = diversity_penalty
        self.minimum_score = minimum_score

    def rerank(
        self,
        query: str,
        candidates: Iterable[RetrievalCandidate],
        *,
        top_k: int = 5,
    ) -> list[RetrievalCandidate]:
        scored = [self._score_candidate(query, candidate) for candidate in candidates]
        filtered = [candidate for candidate in scored if candidate.rerank_score >= self.minimum_score]
        filtered.sort(key=lambda candidate: candidate.rerank_score, reverse=True)
        return self._select_diverse(filtered, top_k=top_k)

    def _score_candidate(self, query: str, candidate: RetrievalCandidate) -> RetrievalCandidate:
        title_text = candidate.title or ""
        title_match = lexical_overlap(query, title_text)
        score = (
            self.similarity_weight * max(0.0, min(candidate.similarity, 1.0))
            + self.lexical_weight * lexical_overlap(query, candidate.text)
            + self.recency_weight * recency_score(candidate.created_at)
            + self.title_weight * title_match
            + SOURCE_TYPE_BOOSTS.get(candidate.source_type, 0.0)
        )
        return replace(candidate, rerank_score=round(score, 6))

    def _select_diverse(
        self,
        candidates: list[RetrievalCandidate],
        *,
        top_k: int,
    ) -> list[RetrievalCandidate]:
        selected: list[RetrievalCandidate] = []
        for candidate in candidates:
            if len(selected) >= top_k:
                break
            penalty = self._max_similarity_to_selected(candidate, selected) * self.diversity_penalty
            adjusted = replace(candidate, rerank_score=round(candidate.rerank_score - penalty, 6))
            selected.append(adjusted)
            selected.sort(key=lambda item: item.rerank_score, reverse=True)
        return selected[:top_k]

    @staticmethod
    def _max_similarity_to_selected(
        candidate: RetrievalCandidate,
        selected: list[RetrievalCandidate],
    ) -> float:
        if not selected:
            return 0.0
        candidate_tokens = tokenize(candidate.text)
        if not candidate_tokens:
            return 0.0
        similarities = []
        for existing in selected:
            existing_tokens = tokenize(existing.text)
            union = candidate_tokens | existing_tokens
            similarities.append(len(candidate_tokens & existing_tokens) / len(union) if union else 0.0)
        return max(similarities, default=0.0)

