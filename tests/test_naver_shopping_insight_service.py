from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import NaverShoppingCategoryOption, NaverShoppingCategorySelection
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService


def test_naver_shopping_insight_service_mock_response_and_summary(monkeypatch) -> None:
    monkeypatch.setenv("NAVER_DATALAB_CLIENT_ID", "")
    monkeypatch.setenv("NAVER_DATALAB_CLIENT_SECRET", "")
    monkeypatch.setenv(
        "NAVER_SHOPPING_CATEGORY_OPTIONS_JSON",
        '[{"code":"50000000","label":"패션의류","description":"의류 판매"}]',
    )
    get_settings.cache_clear()

    service = NaverShoppingInsightService()
    selection = NaverShoppingCategorySelection(code="50000000", label="패션의류", rationale="셀러 상품 판매")
    response = service.fetch(service.build_request(selection))
    evidence = service.build_shopping_evidence(selection=selection, response=response)

    assert response.results
    assert evidence.category_label == "패션의류"
    assert evidence.recent_ratio is not None
    assert "패션의류" in evidence.summary

    get_settings.cache_clear()


def test_naver_shopping_insight_relevance_is_selective() -> None:
    service = NaverShoppingInsightService()

    assert service.is_relevant_niche(
        canonical_name="스마트스토어 정산 누락 방지",
        persona="스마트스토어 셀러",
        problem_summary="상품 판매와 정산 누락을 엑셀로 맞춘다.",
        query_group=["스마트스토어 정산", "셀러 판매 관리"],
    )
    assert not service.is_relevant_niche(
        canonical_name="학원 상담 누락 방지",
        persona="학원 원장",
        problem_summary="전화 상담과 재등록 관리를 수기로 한다.",
        query_group=["학원 상담 관리", "학원 문의 누락"],
    )


def test_llm_mock_select_naver_shopping_category_returns_first_option(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    service = OpenAIResearchService()
    selection = service.select_naver_shopping_category(
        canonical_name="스마트스토어 리뷰 관리",
        persona="소형 셀러",
        problem_summary="상품 리뷰 대응과 판매 운영이 분산되어 있다.",
        query_group=["스마트스토어 리뷰 관리", "셀러 상품 운영"],
        options=[
            NaverShoppingCategoryOption(code="50000000", label="패션의류", description="의류 판매"),
            NaverShoppingCategoryOption(code="50000001", label="화장품/미용", description="뷰티 판매"),
        ],
    )

    assert selection.code == "50000000"
    assert selection.label == "패션의류"

    get_settings.cache_clear()
