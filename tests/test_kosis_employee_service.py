from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    KosisIndustryOption,
    KosisIndustrySelection,
    KosisProfileResponse,
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


def test_kosis_profile_requests_support_multi_metric_profiles(monkeypatch) -> None:
    monkeypatch.setenv("KOSIS_API_KEY", "test-key")
    monkeypatch.setenv(
        "KOSIS_PROFILE_OPTIONS_JSON",
        (
            '[{"name":"business-structure","label":"Business structure","kind":"structure","tbl_id":"DT_1F2A01",'
            '"metrics":{"business_count":"T1","employee_count":"T2"},"static_params":{"PRD_SE":"A"},'
            '"industry_dimension_key":"objL1","time_range":[2019,2023]}]'
        ),
    )
    get_settings.cache_clear()

    service = KosisEmployeeService()
    requests = service.build_requests(
        KosisIndustrySelection(code="G47", label="전자상거래 소매", rationale="적합"),
    )

    assert len(requests) == 2
    assert {item.metric_key for item in requests} == {"business_count", "employee_count"}
    assert all(item.start_year == 2019 for item in requests)
    assert all(item.end_year == 2023 for item in requests)
    assert all(item.params["objL1"] == "G47" for item in requests)
    assert all("prdSe" not in item.params for item in requests)
    assert all(item.params["PRD_SE"] == "A" for item in requests)

    get_settings.cache_clear()


def test_kosis_industry_options_support_mapping_shape(monkeypatch) -> None:
    monkeypatch.setenv(
        "KOSIS_INDUSTRY_OPTIONS_JSON",
        '{"classification":"KSIC10","level":"중분류","mapping":{"스마트스토어":"G47912","온라인교육":"P85659"}}',
    )
    get_settings.cache_clear()

    service = KosisEmployeeService()
    options = service.industry_options()

    assert [item.label for item in options] == ["스마트스토어", "온라인교육"]
    assert [item.code for item in options] == ["G47912", "P85659"]

    get_settings.cache_clear()


def test_kosis_build_market_context_aggregates_profiles() -> None:
    service = KosisEmployeeService()
    selection = KosisIndustrySelection(code="G47912", label="통신판매업", rationale="셀러 세그먼트")
    responses = [
        KosisProfileResponse(
            profile_name="business-structure",
            profile_label="Business structure",
            profile_kind="structure",
            metric_key="business_count",
            source_label="KOSIS / structure",
            source_table_id="DT_1F2A01",
            industry_code="G47912",
            industry_label="통신판매업",
            start_year=2019,
            end_year=2023,
            latest_value=1000,
            cagr=0.08,
            series=[],
            rows=[],
        ),
        KosisProfileResponse(
            profile_name="business-structure",
            profile_label="Business structure",
            profile_kind="structure",
            metric_key="employee_count",
            source_label="KOSIS / structure",
            source_table_id="DT_1F2A01",
            industry_code="G47912",
            industry_label="통신판매업",
            start_year=2019,
            end_year=2023,
            latest_value=1800,
            cagr=0.05,
            series=[],
            rows=[],
        ),
        KosisProfileResponse(
            profile_name="service-economics",
            profile_label="Service economics",
            profile_kind="economics",
            metric_key="revenue",
            source_label="KOSIS / economics",
            source_table_id="DT_1SB1501",
            industry_code="G47912",
            industry_label="통신판매업",
            start_year=2019,
            end_year=2023,
            latest_value=900000,
            series=[],
            rows=[],
        ),
    ]

    context = service.build_market_context(selection=selection, responses=responses, rationale="셀러 운영")

    assert context.business_count == 1000
    assert context.employee_count == 1800
    assert context.revenue == 900000
    assert context.revenue_per_employee == 500
    assert context.business_cagr == 0.08
    assert context.employee_cagr == 0.05
    assert "사업체 수는 약 1,000개" in context.summary


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
