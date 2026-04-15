from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, TypeAdapter

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    CandidateGenerationPayload,
    CandidateGenerationResult,
    FinalAnalysisInput,
    FinalAnalysisOutput,
    KosisIndustryOption,
    KosisIndustrySelection,
    NaverShoppingCategoryOption,
    NaverShoppingCategorySelection,
    ProblemCandidateGenerated,
    QueryExpansionResult,
    SeedCategoryDiscoveryPayload,
    SeedCategoryDiscoveryResult,
)


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OpenAIResearchService:
    DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = (getattr(self.settings, "llm_provider", "openai") or "openai").strip().lower()
        self.client = None
        if self.provider == "openai" and self.settings.openai_api_key:
            base_url = (self.settings.openai_base_url or "").strip()
            if not base_url:
                os.environ.pop("OPENAI_BASE_URL", None)
                base_url = self.DEFAULT_OPENAI_BASE_URL
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=base_url,
            )

    def generate_candidates(self, seed_category: str, candidate_count: int) -> CandidateGenerationResult:
        system_prompt = self._load_prompt("candidate_generation.md")
        user_prompt = (
            f"Seed category: {seed_category}\n"
            f"Candidate count target: {candidate_count}\n"
            "Focus on Korean operational pain points for a solo founder.\n"
            "Constraint: return only vertical-market candidates for a specific industry or operator segment."
        )
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_candidates(seed_category, candidate_count)
        payload = self._structured_response(
            model=self._candidate_model(),
            instructions=system_prompt,
            user_prompt=user_prompt,
            schema=CandidateGenerationPayload,
        )
        return CandidateGenerationResult(candidates=payload.candidates)

    def generate_seed_categories(self, seed_count: int) -> SeedCategoryDiscoveryResult:
        system_prompt = self._load_prompt("seed_generation.md")
        user_prompt = (
            f"Seed count target: {seed_count}\n"
            "Goal: find diverse Korean operational domains where recurring, software-solvable pain points are likely.\n"
            "Avoid celebrity/news/trend topics and prefer durable small-business workflows.\n"
            "Constraint: return only vertical-market seeds, not horizontal software categories."
        )
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_seed_categories(seed_count)
        payload = self._structured_response(
            model=self._candidate_model(),
            instructions=system_prompt,
            user_prompt=user_prompt,
            schema=SeedCategoryDiscoveryPayload,
        )
        return SeedCategoryDiscoveryResult(seeds=payload.seeds)

    def analyze_top_candidate(self, payload: FinalAnalysisInput) -> FinalAnalysisOutput:
        system_prompt = self._load_prompt("final_analysis.md")
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_final_analysis(payload)
        return self._structured_response(
            model=self._final_model(),
            instructions=system_prompt,
            user_prompt=payload.model_dump_json(indent=2),
            schema=FinalAnalysisOutput,
            reasoning_effort=self.settings.openai_reasoning_effort,
            text_verbosity=self.settings.openai_text_verbosity,
        )

    def select_kosis_industry(
        self,
        *,
        canonical_name: str,
        persona: str,
        problem_summary: str,
        query_group: list[str],
        options: list[KosisIndustryOption],
    ) -> KosisIndustrySelection:
        system_prompt = self._load_prompt("kosis_industry_mapping.md")
        payload = {
            "canonical_name": canonical_name,
            "persona": persona,
            "problem_summary": problem_summary,
            "query_group": query_group,
            "industry_options": [item.model_dump(mode="json") for item in options],
        }
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_kosis_industry(options)
        return self._structured_response(
            model=self._candidate_model(),
            instructions=system_prompt,
            user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
            schema=KosisIndustrySelection,
        )

    def select_naver_shopping_category(
        self,
        *,
        canonical_name: str,
        persona: str,
        problem_summary: str,
        query_group: list[str],
        options: list[NaverShoppingCategoryOption],
    ) -> NaverShoppingCategorySelection:
        system_prompt = self._load_prompt("naver_shopping_category_mapping.md")
        payload = {
            "canonical_name": canonical_name,
            "persona": persona,
            "problem_summary": problem_summary,
            "query_group": query_group,
            "category_options": [item.model_dump(mode="json") for item in options],
        }
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_naver_shopping_category(options)
        return self._structured_response(
            model=self._candidate_model(),
            instructions=system_prompt,
            user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
            schema=NaverShoppingCategorySelection,
        )

    def expand_queries(self, candidate: ProblemCandidateGenerated) -> QueryExpansionResult:
        system_prompt = self._load_prompt("query_expansion.md")
        if self.provider == "openai" and not self.settings.openai_api_key:
            return self._mock_query_expansion(candidate)
        return self._structured_response(
            model=self._candidate_model(),
            instructions=system_prompt,
            user_prompt=candidate.model_dump_json(indent=2),
            schema=QueryExpansionResult,
        )

    def _candidate_model(self) -> str:
        if self.provider == "codex":
            return getattr(self.settings, "codex_candidate_model", None) or self.settings.openai_candidate_model
        return self.settings.openai_candidate_model

    def _final_model(self) -> str:
        if self.provider == "codex":
            return getattr(self.settings, "codex_final_model", None) or self.settings.openai_final_model
        return self.settings.openai_final_model

    def _codex_structured_response(
        self,
        *,
        model: str,
        instructions: str,
        user_prompt: str,
        schema: type[SchemaT],
    ) -> SchemaT:
        schema_dict = schema.model_json_schema()
        prompt = (
            f"{instructions}\n\n"
            "Return valid JSON only. Do not include markdown fences, commentary, or extra text.\n"
            f"The JSON must satisfy this schema:\n{json.dumps(schema_dict, ensure_ascii=False)}\n\n"
            f"User request:\n{user_prompt}\n"
        )
        cmd = [getattr(self.settings, "codex_bin", "codex"), "exec"]
        if model:
            cmd += ["-m", model]
        cmd.append(prompt)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,
            cwd=Path(__file__).resolve().parents[3],
        )
        if result.returncode != 0:
            raise RuntimeError(f"Codex exec failed: {result.stderr.strip() or result.stdout.strip()}")
        raw = result.stdout.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(f"Codex output did not contain JSON: {raw[:400]}")
        payload = json.loads(raw[start : end + 1])
        return TypeAdapter(schema).validate_python(payload)

    def _structured_response(
        self,
        *,
        model: str,
        instructions: str,
        user_prompt: str,
        schema: type[SchemaT],
        reasoning_effort: str | None = None,
        text_verbosity: str | None = None,
    ) -> SchemaT:
        if self.provider == "codex":
            return self._codex_structured_response(
                model=model,
                instructions=instructions,
                user_prompt=user_prompt,
                schema=schema,
            )
        if self.client is None:
            raise RuntimeError("OpenAI client is not configured")
        schema_dict = schema.model_json_schema()
        response = self.client.responses.create(
            model=model,
            instructions=instructions,
            input=user_prompt,
            reasoning={"effort": reasoning_effort} if reasoning_effort else None,
            text={
                "verbosity": text_verbosity or "low",
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": schema_dict,
                    "strict": True,
                },
            },
        )
        return TypeAdapter(schema).validate_python(json.loads(response.output_text))

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).resolve().parents[3] / "prompts" / filename
        return path.read_text(encoding="utf-8").strip()

    def _mock_candidates(self, seed_category: str, candidate_count: int) -> CandidateGenerationResult:
        canned = [
            {
                "seed_category": seed_category,
                "persona": "소형 네이버 셀러",
                "buyer": "스토어 대표 셀러",
                "job_to_be_done": "경쟁 상품 가격과 리뷰 변화를 주기적으로 확인한다",
                "pain": "수작업 확인에 시간이 많이 들고 누락이 생긴다",
                "quantified_loss": "매일 30-60분이 가격 확인에 쓰이고 할인 타이밍을 놓치면 전환 손실이 생긴다.",
                "current_spend": "엑셀과 수동 검색, 대표자 시간을 계속 투입한다.",
                "repeat_frequency": "daily",
                "current_workaround": ["엑셀", "수동 검색", "캡처"],
                "software_fit": "high",
                "payment_likelihood": "medium",
                "online_gtm_fit": "high",
                "market_size_confidence": "high",
                "decision_maker_clarity": "high",
                "manual_first_viability": "high",
                "integration_lightness": "high",
                "risk_flags": ["depends_on_external_platform"],
                "query_candidates": [
                    "스마트스토어 경쟁사 가격 확인",
                    "네이버쇼핑 가격 모니터링",
                    "경쟁상품 추적",
                    "상품 리뷰 모니터링",
                ],
                "online_demand_hypothesis": "셀러가 검색과 커뮤니티에서 가격 모니터링 도구를 반복적으로 찾을 가능성이 높다.",
                "online_acquisition_channels": ["네이버 검색", "셀러 커뮤니티", "블로그 SEO"],
            },
            {
                "seed_category": seed_category,
                "persona": "소형 학원 원장",
                "buyer": "학원 원장",
                "job_to_be_done": "보강과 결석 일정을 학부모 커뮤니케이션과 함께 관리한다",
                "pain": "카톡과 엑셀로 관리해 실수가 잦고 공지가 늦어진다",
                "quantified_loss": "주당 여러 번 공지 누락과 상담 시간이 추가로 발생하고 학부모 불만으로 이어질 수 있다.",
                "current_spend": "원장과 상담실장이 카카오톡과 엑셀로 직접 대응한다.",
                "repeat_frequency": "weekly",
                "current_workaround": ["카카오톡", "엑셀", "수기 메모"],
                "software_fit": "high",
                "payment_likelihood": "high",
                "online_gtm_fit": "medium",
                "market_size_confidence": "high",
                "decision_maker_clarity": "high",
                "manual_first_viability": "high",
                "integration_lightness": "medium",
                "risk_flags": [],
                "query_candidates": [
                    "학원 보강 관리",
                    "학원 결석 관리 프로그램",
                    "보강 일정 관리",
                    "학원 출결 관리",
                ],
                "online_demand_hypothesis": "학원 운영 검색 수요와 원장 대상 커뮤니티에서 운영툴 탐색 수요가 존재할 가능성이 높다.",
                "online_acquisition_channels": ["네이버 검색", "원장 커뮤니티", "콘텐츠 SEO"],
            },
        ]
        items = (canned * ((candidate_count // len(canned)) + 1))[:candidate_count]
        return CandidateGenerationResult.model_validate({"candidates": items})

    def _mock_final_analysis(self, payload: FinalAnalysisInput) -> FinalAnalysisOutput:
        return FinalAnalysisOutput(
            title=f"{payload.canonical_name} | {payload.persona} 운영 기회",
            niche_name=payload.canonical_name,
            persona=payload.persona,
            buyer=payload.buyer,
            problem_summary=payload.problem_summary,
            core_value_proposition=(
                f"{payload.buyer}가 {payload.problem_summary}로 생기는 시간 손실과 누락을 줄이도록 "
                f"{payload.canonical_name} 핵심 흐름만 먼저 자동화한다."
            ),
            landing_page_hook=f"{payload.buyer}용 {payload.canonical_name}. {payload.quantified_loss}",
            saas_fit_score=int(round(payload.score_breakdown.final_score)),
            trend_signal_score=int(round(payload.score_breakdown.online_demand * 100)),
            payment_likelihood="medium-high" if payload.score_breakdown.payment_likelihood >= 0.65 else "medium",
            implementation_feasibility=(
                "high" if payload.score_breakdown.implementation_feasibility >= 0.7 else "medium"
            ),
            mvp_idea=["문제 대상 등록", "변동 탐지 대시보드", "주간 요약 리포트", "우선순위 알림"],
            go_to_market=["네이버 검색 랜딩 페이지", "업계 커뮤니티", "실무형 블로그 SEO"],
            first_10_leads=[
                f"{payload.persona}가 모이는 네이버 카페 운영자/활동자 3명",
                f"{payload.persona} 대상 블로그/유튜브 운영자 3명",
                f"{payload.canonical_name} 관련 질문 글 작성자 4명",
            ],
            interview_questions=[
                "이 문제는 한 주에 몇 번 반복되나?",
                "최근 이 문제로 생긴 시간 손실이나 매출 손실은 무엇이었나?",
                "지금은 누가 어떤 방식으로 해결하고 있나?",
                "기존 도구를 안 쓰는 이유는 가격, 복잡도, 업종 부적합 중 무엇인가?",
                "초기 자동화가 부족해도 수작업 대행 형태로 비용을 낼 의향이 있나?",
            ],
            manual_first_offer=[
                "초기에는 폼 또는 파일 업로드를 받아 사람이 직접 정리한 결과를 전달한다.",
                "가장 아픈 한 단계만 먼저 대신 처리해 반복 사용 여부를 본다.",
                "대행 과정에서 공통 패턴이 확인되면 그 부분만 자동화한다.",
            ],
            price_test=[
                "월 3만원 테스트",
                "월 7만원 테스트",
                "월 15만원 테스트",
            ],
            must_have_scope=[
                "핵심 입력 한 가지",
                "상태/누락 확인 한 화면",
                "알림 또는 후속조치 자동화 한 가지",
            ],
            must_not_build_scope=[
                "ERP/CRM/POS 전체 대체",
                "업종 전체를 커버하는 올인원 백오피스",
                "초기부터 복잡한 양방향 연동과 대규모 권한 체계",
            ],
            online_demand_summary=(
                " ".join(
                    part
                    for part in (
                        payload.search_evidence_context.summary if payload.search_evidence_context else None,
                        payload.absolute_demand_context.summary if payload.absolute_demand_context else None,
                    )
                    if part
                )
                or "온라인 검색 수요 근거는 아직 연결되지 않았다."
            ),
            market_size_summary=(
                " ".join(
                    part
                    for part in (
                        payload.market_size_context.summary if payload.market_size_context else None,
                        payload.pricing_evidence_context.summary if payload.pricing_evidence_context else None,
                    )
                    if part
                )
                or "시장 규모 참고 데이터는 아직 연결되지 않았다."
            ),
            market_size_sufficiency_summary=(
                "solo founder 기준으로 충분 시장으로 보인다."
                if payload.features.market_size_sufficiency_score >= 0.65
                else "시장 규모는 참고 수준이며 충분성 판단은 보수적으로 봐야 한다."
            ),
            search_evidence_summary=(
                payload.search_evidence_context.summary
                if payload.search_evidence_context
                else "검색 기반 참고 데이터는 아직 연결되지 않았다."
            ),
            shopping_evidence_summary=(
                payload.shopping_evidence_context.summary
                if payload.shopping_evidence_context
                else "쇼핑 클릭 기반 참고 데이터는 아직 연결되지 않았다."
            ),
            public_data_summary=(
                payload.public_data_context.summary
                if payload.public_data_context
                else "활용 가능한 공공데이터 연계 관점은 아직 정리되지 않았다."
            ),
            online_gtm_summary=(
                payload.online_gtm_context.summary
                if payload.online_gtm_context
                else "온라인 전용 GTM 채널 근거는 아직 정리되지 않았다."
            ),
            recommended_online_channels=(
                payload.online_gtm_context.channel_signals
                if payload.online_gtm_context and payload.online_gtm_context.channel_signals
                else ["네이버 검색", "블로그 SEO", "업종 커뮤니티"]
            ),
            validation_plan=[
                f"{payload.buyer} 5명을 인터뷰해 현재 수작업 빈도와 누락 비용을 확인한다.",
                f"'{payload.canonical_name}' 하나만 설명하는 랜딩페이지를 열고 검색/콘텐츠 유입으로 문의 전환율을 측정한다.",
                "초기에는 수작업 대행 방식으로도 반복 문제 해결 의향과 첫 문의 전환을 검증한다.",
            ],
            kill_criteria=[
                "반복 빈도가 낮거나 긴급도가 낮다는 응답이 다수면 중단한다.",
                "명확한 결제 주체가 끝내 확인되지 않으면 후순위로 내린다.",
                "핵심 문제 해결에 무거운 기존 시스템 교체가 필요하면 보류한다.",
            ],
            risk_flags=payload.risk_flags,
            recommended_priority=1,
        )

    def _mock_kosis_industry(self, options: list[KosisIndustryOption]) -> KosisIndustrySelection:
        if not options:
            raise RuntimeError("No KOSIS industry options are configured")
        chosen = options[0]
        return KosisIndustrySelection(
            code=chosen.code,
            label=chosen.label,
            rationale=f"{chosen.label}이(가) 문제 영역과 가장 가깝다.",
        )

    def _mock_naver_shopping_category(self, options: list[NaverShoppingCategoryOption]) -> NaverShoppingCategorySelection:
        if not options:
            raise RuntimeError("No Naver shopping category options are configured")
        chosen = options[0]
        return NaverShoppingCategorySelection(
            code=chosen.code,
            label=chosen.label,
            rationale=f"{chosen.label} 카테고리가 상품 판매 맥락과 가장 가깝다.",
        )

    def _mock_seed_categories(self, seed_count: int) -> SeedCategoryDiscoveryResult:
        canned = [
            {
                "name": "스마트스토어 운영",
                "description": "소형 셀러의 상품관리, 가격확인, 리뷰대응, 정산 점검 같은 반복 업무를 다룬다.",
                "rationale": "한국 검색 수요가 풍부하고 반복 업무가 뚜렷해 마이크로 SaaS 기회 탐색에 적합하다.",
            },
            {
                "name": "학원 운영",
                "description": "출결, 보강, 상담, 학부모 공지, 수납 확인 등 학원 운영 반복 업무를 다룬다.",
                "rationale": "전화·카톡·엑셀에 의존하는 경우가 많아 구조화된 운영 자동화 니즈가 크다.",
            },
            {
                "name": "병원 상담 운영",
                "description": "예약 리마인드, 상담 후속조치, 문의 분류, 재내원 유도 업무를 다룬다.",
                "rationale": "상담 파이프라인이 반복적이고 누락 비용이 높아 소프트웨어 가치가 높다.",
            },
            {
                "name": "부동산 중개 운영",
                "description": "매물 추적, 고객 문의 응대, 방문 일정 조율, 계약 진행 관리를 다룬다.",
                "rationale": "반복 커뮤니케이션과 수동 정리가 많아 틈새 운영도구 가능성이 높다.",
            },
            {
                "name": "미용실 운영",
                "description": "예약, 재방문 관리, 시술 전후 상담, 노쇼 대응, 직원 스케줄 조정을 다룬다.",
                "rationale": "고객 반복 방문과 운영 자동화 니즈가 분명해 실전 SaaS 문제를 찾기 좋다.",
            },
            {
                "name": "식당 운영",
                "description": "재고 확인, 발주, 예약, 리뷰 대응, 배달 채널 운영 업무를 다룬다.",
                "rationale": "운영 반복성이 높고 외부 채널 의존도가 커서 보조 툴 수요가 발생하기 쉽다.",
            },
            {
                "name": "세무사 사무소 운영",
                "description": "자료 요청, 마감 추적, 고객 커뮤니케이션, 신고 일정 관리 업무를 다룬다.",
                "rationale": "반복 일정과 문서 요청 흐름이 뚜렷해 자동화 포인트를 찾기 좋다.",
            },
            {
                "name": "인테리어 견적 운영",
                "description": "리드 접수, 상담 기록, 견적 비교, 일정 조율, 후속 응대 업무를 다룬다.",
                "rationale": "수기 정리 비중이 높고 영업-운영 연결 문제가 빈번해 도구 수요가 있다.",
            },
        ]
        return SeedCategoryDiscoveryResult.model_validate({"seeds": canned[:seed_count]})

    def _mock_query_expansion(self, candidate: ProblemCandidateGenerated) -> QueryExpansionResult:
        base_queries = list(dict.fromkeys(candidate.query_candidates))
        expanded = list(base_queries)
        suffixes = ["프로그램", "자동화", "관리", "정리", "모니터링"]
        for query in base_queries[:3]:
            for suffix in suffixes:
                expanded.append(f"{query} {suffix}")
        informational = [query for query in expanded if "방법" in query or "정리" in query]
        commercial = [query for query in expanded if "프로그램" in query or "자동화" in query or "관리" in query]
        return QueryExpansionResult(
            seed_category=candidate.seed_category,
            persona=candidate.persona,
            canonical_name=base_queries[0],
            expanded_queries=list(dict.fromkeys(expanded))[:12],
            commercial_queries=list(dict.fromkeys(commercial))[:6],
            informational_queries=list(dict.fromkeys(informational))[:6],
        )
