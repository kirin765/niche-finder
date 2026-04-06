from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    KosisEmployeeResponse,
    KosisIndustryOption,
    KosisIndustrySelection,
)
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.llm_service import OpenAIResearchService


def test_kosis_build_request_merges_static_params(monkeypatch) -> None:
    monkeypatch.setenv("KOSIS_API_KEY", "test-key")
    monkeypatch.setenv("KOSIS_TBL_ID", "DT_1K52D01")
    monkeypatch.setenv("KOSIS_EMPLOYEE_ITM_ID", "T1")
    monkeypatch.setenv("KOSIS_STATIC_PARAMS_JSON", '{"objL2":"ALL"}')
    get_settings.cache_clear()

    service = KosisEmployeeService()
    request = service.build_request(
        KosisIndustrySelection(code="G", label="도매 및 소매업", rationale="적합"),
        reference_year=2023,
    )

    assert request.params["apiKey"] == "test-key"
    assert request.params["tblId"] == "DT_1K52D01"
    assert request.params["itmId"] == "T1"
    assert request.params["objL1"] == "G"
    assert request.params["objL2"] == "ALL"
    assert request.reference_year == 2023

    get_settings.cache_clear()


def test_kosis_build_market_size_context_uses_employee_count() -> None:
    service = KosisEmployeeService()
    response = KosisEmployeeResponse(
        industry_code="P",
        industry_label="교육 서비스업",
        reference_year=2023,
        employee_count=123456,
        source_label=service.SOURCE_LABEL,
        source_table_id="DT_1K52D01",
        rows=[],
    )

    context = service.build_market_size_context(response, rationale="학원 운영과 가장 가깝다.")

    assert context.employee_count == 123456
    assert "123,456명" in context.summary
    assert context.industry_label == "교육 서비스업"


def test_llm_mock_select_kosis_industry_returns_first_option(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    service = OpenAIResearchService()
    selection = service.select_kosis_industry(
        canonical_name="학원 상담 관리",
        persona="학원 원장",
        problem_summary="상담 누락이 잦다.",
        query_group=["학원 상담 관리", "학원 문의 관리"],
        options=[
            KosisIndustryOption(code="P", label="교육 서비스업", description="학원, 교육 서비스"),
            KosisIndustryOption(code="G", label="도매 및 소매업", description="유통, 판매"),
        ],
    )

    assert selection.code == "P"
    assert selection.label == "교육 서비스업"

    get_settings.cache_clear()
