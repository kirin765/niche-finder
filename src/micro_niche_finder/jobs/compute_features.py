from micro_niche_finder.domain.schemas import DataLabResponse, TrendFeatureSet
from micro_niche_finder.services.feature_service import FeatureExtractionService


def run(
    response: DataLabResponse,
    query_count: int,
    queries: list[str],
    feature_service: FeatureExtractionService,
) -> TrendFeatureSet:
    return feature_service.extract(response=response, query_count=query_count, queries=queries)
