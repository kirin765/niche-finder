from micro_niche_finder.domain.schemas import FinalAnalysisInput, FinalAnalysisOutput
from micro_niche_finder.services.llm_service import OpenAIResearchService


class ReportService:
    def __init__(self, llm_service: OpenAIResearchService) -> None:
        self.llm_service = llm_service

    def build_report(self, analysis_input: FinalAnalysisInput) -> FinalAnalysisOutput:
        report = self.llm_service.analyze_top_candidate(analysis_input)
        title = self._build_title(report)
        buyer = self._clean_buyer(report.buyer, analysis_input.buyer, analysis_input.persona)
        core_value_proposition = self._clean_text(
            report.core_value_proposition,
            fallback=(
                f"{buyer}가 {analysis_input.problem_summary} 때문에 생기는 누락과 시간 손실을 줄이도록 "
                f"{analysis_input.canonical_name} 한 개 워크플로만 먼저 자동화한다."
            ),
        )
        landing_page_hook = self._clean_text(
            report.landing_page_hook,
            fallback=f"{buyer}용 {analysis_input.canonical_name}. {analysis_input.quantified_loss}",
        )
        first_10_leads = self._normalize_list(
            report.first_10_leads,
            fallback=[
                f"{buyer}가 모이는 네이버 카페 운영자/활동자에게 직접 인터뷰 요청",
                f"{analysis_input.canonical_name} 관련 질문 글 작성자에게 콜드 아웃리치",
                f"{analysis_input.persona} 대상 블로그/유튜브 운영자에게 피드백 요청",
            ],
        )
        interview_questions = self._normalize_list(
            report.interview_questions,
            fallback=[
                "이 문제는 한 주에 몇 번 반복되나?",
                "최근 이 문제로 생긴 시간 손실이나 매출 손실은 무엇이었나?",
                "지금은 누가 어떤 방식으로 해결하고 있나?",
                "기존 도구를 안 쓰는 이유는 가격, 복잡도, 업종 부적합 중 무엇인가?",
                "초기 자동화가 부족해도 수작업 대행 형태로 비용을 낼 의향이 있나?",
            ],
        )
        manual_first_offer = self._normalize_list(
            report.manual_first_offer,
            fallback=[
                "초기에는 폼 또는 파일 업로드를 받아 사람이 직접 정리한 결과를 전달한다.",
                "가장 아픈 한 단계만 먼저 대신 처리해 반복 사용 여부를 본다.",
                "대행 과정에서 공통 패턴이 확인되면 그 부분만 자동화한다.",
            ],
        )
        price_test = self._normalize_list(
            report.price_test,
            fallback=["월 3만원 테스트", "월 7만원 테스트", "월 15만원 테스트"],
        )
        must_have_scope = self._normalize_list(
            report.must_have_scope,
            fallback=[
                "핵심 입력 한 가지",
                "상태/누락 확인 한 화면",
                "알림 또는 후속조치 자동화 한 가지",
            ],
        )
        must_not_build_scope = self._normalize_list(
            report.must_not_build_scope,
            fallback=[
                "올인원 운영툴",
                "무거운 기존 시스템 교체",
                "복잡한 초기 통합",
            ],
        )
        validation_plan = self._normalize_list(
            report.validation_plan,
            fallback=[
                f"{buyer} 인터뷰 5건으로 현재 수작업 흐름과 누락 비용을 확인한다.",
                f"'{report.niche_name}' 핵심 문제만 담은 랜딩페이지를 만들고 검색광고/콘텐츠 유입으로 클릭 대비 문의 전환율을 측정한다.",
                "수작업 대행 또는 파일 업로드 형태의 manual-first 제안으로 첫 문의 전환을 검증한다.",
            ],
        )
        kill_criteria = self._normalize_list(
            report.kill_criteria,
            fallback=[
                "인터뷰 대상이 문제를 주 1회 이하로 겪는다고 답하면 중단한다.",
                "지불 의사 또는 기존 대체 비용이 확인되지 않으면 후순위로 내린다.",
                "핵심 문제 해결에 외부 핵심 시스템 교체가 필요하면 보류한다.",
            ],
        )
        return report.model_copy(
            update={
                "title": title,
                "buyer": buyer,
                "core_value_proposition": core_value_proposition,
                "landing_page_hook": landing_page_hook,
                "first_10_leads": first_10_leads,
                "interview_questions": interview_questions,
                "manual_first_offer": manual_first_offer,
                "price_test": price_test,
                "must_have_scope": must_have_scope,
                "must_not_build_scope": must_not_build_scope,
                "validation_plan": validation_plan,
                "kill_criteria": kill_criteria,
            }
        )

    def _build_title(self, report: FinalAnalysisOutput) -> str:
        raw = (report.title or "").strip()
        generic_markers = ("daily report", "micro niche", "report", "리포트", "브리프", "보고서")
        if raw and report.niche_name in raw and not self._looks_generic(raw, generic_markers):
            return raw
        if raw and not self._looks_generic(raw, generic_markers):
            return raw
        persona = self._compact_persona(report.persona)
        if persona:
            return f"{report.niche_name} | {persona} 운영 기회"
        return f"{report.niche_name} | 운영 기회 분석"

    @staticmethod
    def _clean_buyer(buyer: str, candidate_buyer: str, persona: str) -> str:
        value = (buyer or "").strip()
        if value:
            return value
        value = (candidate_buyer or "").strip()
        if value:
            return value
        return ReportService._compact_persona(persona) or persona

    @staticmethod
    def _normalize_list(values: list[str], *, fallback: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item and item.strip()]
        return cleaned or fallback

    @staticmethod
    def _clean_text(value: str, *, fallback: str) -> str:
        cleaned = (value or "").strip()
        return cleaned or fallback

    @staticmethod
    def _compact_persona(persona: str) -> str:
        return " ".join((persona or "").split())[:40].strip()

    @staticmethod
    def _looks_generic(text: str, markers: tuple[str, ...]) -> bool:
        normalized = " ".join(text.lower().split())
        return any(marker in normalized for marker in markers)
