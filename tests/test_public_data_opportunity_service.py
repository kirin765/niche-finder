from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService


def test_public_data_service_recommends_commerce_and_validation_sources() -> None:
    service = PublicDataOpportunityService()

    context = service.analyze(
        canonical_name="스마트스토어 셀러 정산 검증",
        persona="소형 셀러",
        problem_summary="사업자 상태와 정산 누락을 매일 엑셀로 점검한다.",
        query_group=["스마트스토어 정산", "통신판매 사업자 확인"],
        risk_flags=[],
    )

    assert context is not None
    dataset_ids = [item.dataset_id for item in context.recommendations]
    assert "15126322" in dataset_ids
    assert "15081808" in dataset_ids
    assert "셀러" in context.summary or "통신판매" in context.summary


def test_public_data_service_warns_on_regulated_verticals() -> None:
    service = PublicDataOpportunityService()

    context = service.analyze(
        canonical_name="의료기기 품목 허가 관리",
        persona="의료기기 유통사 실무자",
        problem_summary="품목 허가와 카탈로그 변경을 수기로 정리한다.",
        query_group=["의료기기 품목허가 관리"],
        risk_flags=["regulation_risk"],
    )

    assert context is not None
    assert any(item.dataset_id == "15057456" for item in context.recommendations)
    assert "규제" in context.summary
