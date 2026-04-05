from micro_niche_finder.services.datalab_service import NaverDataLabService


def test_build_request_limits_keywords_to_20_unique_items() -> None:
    service = NaverDataLabService()
    queries = [f"키워드 {index}" for index in range(25)] + ["키워드 1", "  키워드 2  "]

    request = service.build_request(group_name="아주 긴 그룹 이름" * 10, queries=queries)

    assert len(request.keywordGroups[0].keywords) == 20
    assert request.keywordGroups[0].keywords[0] == "키워드 0"
    assert request.keywordGroups[0].keywords[-1] == "키워드 19"
    assert len(request.keywordGroups[0].groupName) <= 50
