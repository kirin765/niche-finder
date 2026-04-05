from micro_niche_finder.domain.schemas import DataLabResponse
from micro_niche_finder.services.datalab_service import NaverDataLabService


def run(
    *,
    canonical_name: str,
    queries: list[str],
    datalab_service: NaverDataLabService,
) -> DataLabResponse:
    request = datalab_service.build_request(group_name=canonical_name, queries=queries)
    return datalab_service.fetch(request)
