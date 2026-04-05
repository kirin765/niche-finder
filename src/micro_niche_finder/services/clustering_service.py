from collections import defaultdict

from micro_niche_finder.domain.schemas import QueryExpansionResult, QueryGroupNormalized


class QueryClusteringService:
    def normalize_candidate(self, expansion: QueryExpansionResult) -> QueryGroupNormalized:
        normalized = []
        excluded = []
        for query in expansion.expanded_queries:
            cleaned = " ".join(query.strip().split())
            if len(cleaned) < 4 or cleaned in {"마케팅", "자동화", "관리"}:
                excluded.append(cleaned)
                continue
            normalized.append(cleaned)

        canonical = expansion.canonical_name if normalized else expansion.canonical_name[:50]
        overlap = self._overlap_score(normalized)
        return QueryGroupNormalized(
            canonical_name=canonical,
            queries=list(dict.fromkeys(normalized)),
            excluded_queries=list(dict.fromkeys(excluded)),
            overlap_score=overlap,
        )

    def cluster_candidates(self, candidates: list[QueryExpansionResult]) -> dict[int, QueryGroupNormalized]:
        grouped: dict[int, QueryGroupNormalized] = {}
        for index, candidate in enumerate(candidates):
            grouped[index] = self.normalize_candidate(candidate)
        return grouped

    @staticmethod
    def _overlap_score(queries: list[str]) -> float:
        if len(queries) < 2:
            return 1.0
        token_count = defaultdict(int)
        for query in queries:
            for token in set(query.split()):
                token_count[token] += 1
        shared = sum(1 for count in token_count.values() if count > 1)
        total = max(len(token_count), 1)
        return round(shared / total, 4)
