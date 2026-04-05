from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, TypeAdapter

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    CandidateGenerationResult,
    FinalAnalysisInput,
    FinalAnalysisOutput,
    ProblemCandidateGenerated,
    QueryExpansionResult,
)


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OpenAIResearchService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = None
        if self.settings.openai_api_key:
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
            )

    def generate_candidates(self, seed_category: str, candidate_count: int) -> CandidateGenerationResult:
        system_prompt = self._load_prompt("candidate_generation.md")
        user_prompt = (
            f"Seed category: {seed_category}\n"
            f"Candidate count target: {candidate_count}\n"
            "Focus on Korean operational pain points for a solo founder."
        )
        if not self.settings.openai_api_key:
            return self._mock_candidates(seed_category, candidate_count)
        return self._structured_response(
            model=self.settings.openai_candidate_model,
            instructions=system_prompt,
            user_prompt=user_prompt,
            schema=CandidateGenerationResult,
        )

    def analyze_top_candidate(self, payload: FinalAnalysisInput) -> FinalAnalysisOutput:
        system_prompt = self._load_prompt("final_analysis.md")
        if not self.settings.openai_api_key:
            return self._mock_final_analysis(payload)
        return self._structured_response(
            model=self.settings.openai_final_model,
            instructions=system_prompt,
            user_prompt=payload.model_dump_json(indent=2),
            schema=FinalAnalysisOutput,
            reasoning_effort=self.settings.openai_reasoning_effort,
            text_verbosity=self.settings.openai_text_verbosity,
        )

    def expand_queries(self, candidate: ProblemCandidateGenerated) -> QueryExpansionResult:
        system_prompt = self._load_prompt("query_expansion.md")
        if not self.settings.openai_api_key:
            return self._mock_query_expansion(candidate)
        return self._structured_response(
            model=self.settings.openai_candidate_model,
            instructions=system_prompt,
            user_prompt=candidate.model_dump_json(indent=2),
            schema=QueryExpansionResult,
        )

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
                "job_to_be_done": "경쟁 상품 가격과 리뷰 변화를 주기적으로 확인한다",
                "pain": "수작업 확인에 시간이 많이 들고 누락이 생긴다",
                "repeat_frequency": "daily",
                "current_workaround": ["엑셀", "수동 검색", "캡처"],
                "software_fit": "high",
                "payment_likelihood": "medium",
                "risk_flags": ["depends_on_external_platform"],
                "query_candidates": [
                    "스마트스토어 경쟁사 가격 확인",
                    "네이버쇼핑 가격 모니터링",
                    "경쟁상품 추적",
                    "상품 리뷰 모니터링",
                ],
            },
            {
                "seed_category": seed_category,
                "persona": "소형 학원 원장",
                "job_to_be_done": "보강과 결석 일정을 학부모 커뮤니케이션과 함께 관리한다",
                "pain": "카톡과 엑셀로 관리해 실수가 잦고 공지가 늦어진다",
                "repeat_frequency": "weekly",
                "current_workaround": ["카카오톡", "엑셀", "수기 메모"],
                "software_fit": "high",
                "payment_likelihood": "high",
                "risk_flags": [],
                "query_candidates": [
                    "학원 보강 관리",
                    "학원 결석 관리 프로그램",
                    "보강 일정 관리",
                    "학원 출결 관리",
                ],
            },
        ]
        items = (canned * ((candidate_count // len(canned)) + 1))[:candidate_count]
        return CandidateGenerationResult.model_validate({"candidates": items})

    def _mock_final_analysis(self, payload: FinalAnalysisInput) -> FinalAnalysisOutput:
        return FinalAnalysisOutput(
            niche_name=payload.canonical_name,
            persona=payload.persona,
            problem_summary=payload.problem_summary,
            saas_fit_score=int(round(payload.score_breakdown.final_score)),
            trend_signal_score=int(round(payload.score_breakdown.persistent_signal * 100)),
            payment_likelihood="medium-high" if payload.score_breakdown.payment_likelihood >= 0.65 else "medium",
            implementation_feasibility=(
                "high" if payload.score_breakdown.implementation_feasibility >= 0.7 else "medium"
            ),
            mvp_idea=[
                "문제 대상 등록",
                "변동 탐지 대시보드",
                "주간 요약 리포트",
                "우선순위 알림",
            ],
            go_to_market=["네이버 검색 랜딩 페이지", "업계 커뮤니티", "실무형 블로그 SEO"],
            risk_flags=payload.risk_flags,
            recommended_priority=1,
        )

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
