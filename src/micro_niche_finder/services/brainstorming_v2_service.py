from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from micro_niche_finder.domain.schemas import FinalAnalysisInput, FinalAnalysisOutput
from micro_niche_finder.services.report_service import ReportService


TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


@dataclass(slots=True)
class BrainstormingCandidateV2:
    candidate_id: int
    seed_id: int
    seed_name: str
    canonical_name: str
    persona: str
    problem_summary: str
    analysis_input: FinalAnalysisInput
    base_score: float
    novelty_score: float
    diversity_score: float
    evidence_score: float
    final_score: float
    nearest_similarity: float
    nearest_report_name: str | None
    why_different: str
    evidence_summary: str


class BrainstormingV2Service:
    def __init__(self, report_service: ReportService) -> None:
        self.report_service = report_service

    def rank_candidates(
        self,
        *,
        session: Session,
        scored_payloads: list[tuple[float, int, int, str, FinalAnalysisInput]],
    ) -> list[BrainstormingCandidateV2]:
        recent_reports = self._load_recent_reports(session)
        recent_seed_counts = Counter(item["seed_name"] for item in recent_reports)
        ranked: list[BrainstormingCandidateV2] = []

        for base_score, candidate_id, seed_id, seed_name, analysis_input in scored_payloads:
            novelty_score, nearest_similarity, nearest_name = self._novelty_against_recent(
                analysis_input=analysis_input,
                recent_reports=recent_reports,
            )
            diversity_score = self._diversity_score(
                seed_name=seed_name,
                persona=analysis_input.persona,
                recent_seed_counts=recent_seed_counts,
            )
            evidence_score = self._evidence_score(analysis_input)
            landing_test_score = self._landing_testability_score(analysis_input)
            final_score = (
                base_score * 0.66
                + novelty_score * 16.0
                + diversity_score * 5.0
                + evidence_score * 3.0
                + landing_test_score * 10.0
            )
            ranked.append(
                BrainstormingCandidateV2(
                    candidate_id=candidate_id,
                    seed_id=seed_id,
                    seed_name=seed_name,
                    canonical_name=analysis_input.canonical_name,
                    persona=analysis_input.persona,
                    problem_summary=analysis_input.problem_summary,
                    analysis_input=analysis_input,
                    base_score=round(base_score, 2),
                    novelty_score=round(novelty_score, 4),
                    diversity_score=round(diversity_score, 4),
                    evidence_score=round(evidence_score, 4),
                    final_score=round(final_score, 2),
                    nearest_similarity=round(nearest_similarity, 4),
                    nearest_report_name=nearest_name,
                    why_different=self._why_different(analysis_input, nearest_name, nearest_similarity),
                    evidence_summary=self._evidence_summary(analysis_input),
                )
            )

        ranked.sort(key=lambda item: item.final_score, reverse=True)
        return ranked

    def build_report(self, candidate: BrainstormingCandidateV2) -> FinalAnalysisOutput:
        report = self.report_service.build_report(candidate.analysis_input)
        payload = report.model_dump()
        payload["search_evidence_summary"] = self._merge_texts(
            candidate.evidence_summary,
            payload.get("search_evidence_summary") or "",
        )
        payload["online_gtm_summary"] = self._merge_texts(
            f"차별성 판단: {candidate.why_different}",
            payload.get("online_gtm_summary") or "",
        )
        return FinalAnalysisOutput.model_validate(payload)

    def _load_recent_reports(self, session: Session) -> list[dict[str, Any]]:
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        rows = session.execute(
            text(
                """
                SELECT s.name AS seed_name, f.report_json AS report_json
                FROM final_reports f
                JOIN problem_candidates p ON p.id = f.problem_candidate_id
                JOIN seed_categories s ON s.id = p.seed_category_id
                WHERE f.created_at >= :cutoff
                ORDER BY f.created_at DESC
                LIMIT 20
                """
            ),
            {"cutoff": cutoff},
        ).fetchall()
        result = []
        for row in rows:
            report_json = row[1] or {}
            if isinstance(report_json, str):
                try:
                    report_json = json.loads(report_json)
                except Exception:
                    report_json = {}
            result.append(
                {
                    "seed_name": row[0],
                    "niche_name": report_json.get("niche_name", ""),
                    "persona": report_json.get("persona", ""),
                    "problem_summary": report_json.get("problem_summary", ""),
                }
            )
        return result

    def _novelty_against_recent(
        self,
        *,
        analysis_input: FinalAnalysisInput,
        recent_reports: list[dict[str, Any]],
    ) -> tuple[float, float, str | None]:
        current = self._tokenize(
            " ".join([analysis_input.canonical_name, analysis_input.persona, analysis_input.problem_summary])
        )
        if not current:
            return 0.5, 0.0, None
        nearest_similarity = 0.0
        nearest_name = None
        for item in recent_reports:
            other = self._tokenize(
                " ".join([item.get("niche_name", ""), item.get("persona", ""), item.get("problem_summary", "")])
            )
            similarity = self._jaccard(current, other)
            if similarity > nearest_similarity:
                nearest_similarity = similarity
                nearest_name = item.get("niche_name") or None
        novelty = max(0.0, 1.0 - nearest_similarity)
        if nearest_similarity >= 0.72:
            novelty *= 0.25
        elif nearest_similarity >= 0.55:
            novelty *= 0.55
        return novelty, nearest_similarity, nearest_name

    def _diversity_score(self, *, seed_name: str, persona: str, recent_seed_counts: Counter) -> float:
        seed_repeat = recent_seed_counts.get(seed_name, 0)
        seed_penalty = min(0.8, seed_repeat * 0.18)
        solo_bonus = 0.12 if any(marker in persona for marker in ("1인", "소형", "원장", "셀러", "실장")) else 0.0
        return max(0.0, min(1.0, 0.8 - seed_penalty + solo_bonus))

    def _evidence_score(self, analysis_input: FinalAnalysisInput) -> float:
        evidence_flags = [
            analysis_input.search_evidence_context is not None,
            analysis_input.absolute_demand_context is not None,
            analysis_input.market_size_context is not None,
            analysis_input.pricing_evidence_context is not None,
            analysis_input.online_gtm_context is not None,
            analysis_input.public_data_context is not None,
        ]
        filled = sum(1 for item in evidence_flags if item)
        base = filled / len(evidence_flags)
        demand_bonus = min(0.15, analysis_input.features.online_demand_score * 0.1)
        confidence_bonus = min(0.15, analysis_input.features.payability_score * 0.1)
        return min(1.0, base + demand_bonus + confidence_bonus)

    def _why_different(
        self,
        analysis_input: FinalAnalysisInput,
        nearest_name: str | None,
        nearest_similarity: float,
    ) -> str:
        if not nearest_name:
            return "최근 리포트와 직접 비교 가능한 유사 사례가 적었다."
        if nearest_similarity < 0.35:
            return f"최근 리포트인 '{nearest_name}' 대비 문제 문맥과 검색 의도가 충분히 다르다."
        if nearest_similarity < 0.55:
            return f"최근 리포트인 '{nearest_name}'와 일부 키워드는 겹치지만 페르소나 또는 workflow 초점이 다르다."
        return f"최근 리포트인 '{nearest_name}'와 유사성이 있어도, 이번 후보는 페르소나와 실행 wedge를 더 좁게 잡아 차별화했다."

    def _landing_testability_score(self, analysis_input: FinalAnalysisInput) -> float:
        channels = analysis_input.online_gtm_context.channel_signals if analysis_input.online_gtm_context else []
        trackable_channel_score = min(
            1.0,
            sum(1 for channel in channels if any(marker in channel.lower() for marker in ("검색", "광고", "seo", "블로그", "유튜브", "커뮤니티", "카페")))
            / 4,
        )
        score = analysis_input.features.absolute_demand_score * 0.4
        score += analysis_input.features.online_gtm_efficiency_score * 0.25
        score += (1.0 - analysis_input.features.keyword_difficulty_score) * 0.15
        score += analysis_input.features.commercial_intent_ratio * 0.1
        score += trackable_channel_score * 0.1
        return max(0.0, min(1.0, score))

    def _evidence_summary(self, analysis_input: FinalAnalysisInput) -> str:
        parts: list[str] = []
        if analysis_input.absolute_demand_context and analysis_input.absolute_demand_context.summary:
            parts.append(analysis_input.absolute_demand_context.summary)
        if analysis_input.search_evidence_context and analysis_input.search_evidence_context.summary:
            parts.append(analysis_input.search_evidence_context.summary)
        if analysis_input.pricing_evidence_context and analysis_input.pricing_evidence_context.summary:
            parts.append(analysis_input.pricing_evidence_context.summary)
        if analysis_input.market_size_context and analysis_input.market_size_context.summary:
            parts.append(analysis_input.market_size_context.summary)
        if analysis_input.public_data_context and analysis_input.public_data_context.summary:
            parts.append(analysis_input.public_data_context.summary)
        landing_testability = self._landing_testability_score(analysis_input)
        if landing_testability >= 0.7:
            parts.append("랜딩페이지 유입 테스트에 필요한 검색·콘텐츠 트래픽과 측정 가능성이 비교적 높다.")
        elif landing_testability >= 0.5:
            parts.append("랜딩페이지 테스트는 가능하지만, 충분한 클릭과 전환 샘플을 모으려면 키워드 선택을 더 좁혀야 한다.")
        else:
            parts.append("랜딩페이지 전환율을 빠르게 측정하기엔 트래픽 신호가 약한 편이라 우선순위를 낮게 봐야 한다.")
        if not parts:
            return "근거 데이터가 제한적이라 이번 후보는 탐색 신호 중심으로 평가했다."
        text = " ".join(parts)
        return text[:500]

    def _tokenize(self, text: str) -> set[str]:
        return {token.lower() for token in TOKEN_RE.findall(text) if len(token) >= 2}

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _merge_texts(self, left: str, right: str) -> str:
        left = (left or "").strip()
        right = (right or "").strip()
        if not left:
            return right
        if not right:
            return left
        merged = f"{left} {right}"
        return re.sub(r"\s+", " ", merged).strip()
