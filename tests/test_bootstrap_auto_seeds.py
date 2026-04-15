from datetime import datetime

from apps.worker.bootstrap_auto_seeds import _build_raw_markdown, _build_telegram_message, _write_raw_report


def _sample_summary() -> list[dict]:
    return [
        {
            "seed_id": 1,
            "seed_name": "학원 운영",
            "created": True,
            "generated_candidates": 5,
            "reported_candidates": 2,
            "reports": [
                {
                    "recommended_priority": 1,
                    "title": "학원 보강 일정 관리 | 소형 학원 원장 운영 기회",
                    "niche_name": "학원 보강 일정 관리",
                    "persona": "소형 학원 원장",
                    "buyer": "학원 원장",
                    "landing_page_hook": "학원 원장용 학원 보강 일정 관리. 주당 공지 누락이 반복된다.",
                    "core_value_proposition": "보강 누락을 줄이는 데 집중한다.",
                    "validation_plan": ["인터뷰 5건", "랜딩페이지 오픈"],
                    "kill_criteria": ["반복 빈도 낮으면 중단"],
                    "first_10_leads": ["네이버 카페 운영자", "질문 글 작성자"],
                    "price_test": ["월 3만원", "월 7만원"],
                }
            ],
        }
    ]


def test_build_telegram_message_includes_seed_and_report() -> None:
    message = _build_telegram_message(_sample_summary())

    assert "[Auto Seeds Report]" in message
    assert "학원 운영" in message
    assert "학원 보강 일정 관리" in message


def test_write_raw_report_persists_markdown(tmp_path) -> None:
    path = _write_raw_report(str(tmp_path), _sample_summary(), datetime(2026, 4, 14, 12, 0, 0))
    content = _build_raw_markdown(_sample_summary(), datetime(2026, 4, 14, 12, 0, 0))

    written = (tmp_path / "auto-seeds-report-20260414-120000.md").read_text(encoding="utf-8")
    assert path.endswith("auto-seeds-report-20260414-120000.md")
    assert "#### Raw JSON" in written
    assert written == content
