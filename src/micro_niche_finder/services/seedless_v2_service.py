from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from micro_niche_finder.config.database import Base, engine
from micro_niche_finder.domain.schemas import GoogleSearchRequest, IdeaScoreV2Breakdown, NaverSearchRequest
from micro_niche_finder.repos.brainstorming_v2_repo import (
    ClusterMemberRepository,
    EvidencePacketRepository,
    IdeaCandidateV2Repository,
    IdeaScoreV2Repository,
    ProblemClusterRepository,
    ProblemSignalRepository,
    SignalEventRepository,
)


TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


@dataclass(slots=True)
class SeedlessRunSummary:
    signals: int
    clusters: int
    ideas: int
    top_niche: str | None


class SeedlessV2Service:
    DISCOVERY_QUERIES = [
        "미용실 예약금 관리",
        "학원 보강 일정 관리",
        "병원 상담 리마인드",
        "네이버 스마트스토어 가격 모니터링",
        "인테리어 견적 추적",
        "세무사 자료 요청 관리",
        "필라테스 노쇼 관리",
        "반려미용 예약 관리",
    ]

    def __init__(
        self,
        *,
        naver_search_service,
        google_search_service,
        pricing_evidence_service,
        public_data_opportunity_service,
        telegram_service,
    ) -> None:
        self.naver_search_service = naver_search_service
        self.google_search_service = google_search_service
        self.pricing_evidence_service = pricing_evidence_service
        self.public_data_opportunity_service = public_data_opportunity_service
        self.telegram_service = telegram_service
        Base.metadata.create_all(bind=engine)

    def run(self, *, session: Session, send_telegram: bool = False) -> SeedlessRunSummary:
        signal_repo = SignalEventRepository(session)
        problem_signal_repo = ProblemSignalRepository(session)
        cluster_repo = ProblemClusterRepository(session)
        member_repo = ClusterMemberRepository(session)
        idea_repo = IdeaCandidateV2Repository(session)
        evidence_repo = EvidencePacketRepository(session)
        score_repo = IdeaScoreV2Repository(session)

        signal_ids = []
        problem_signals = []
        for query in self.DISCOVERY_QUERIES:
            naver_response = self.naver_search_service.fetch(NaverSearchRequest(query=query, display=5))
            google_response = self.google_search_service.fetch(GoogleSearchRequest(q=query, num=5))
            for item in naver_response.items[:3]:
                raw_text = " ".join(part for part in [item.title or "", item.description or "", query] if part)
                event = signal_repo.create(
                    source_type="naver_search",
                    source_key=query,
                    raw_text=raw_text,
                    normalized_text=self._normalize(raw_text),
                    url=item.link,
                    title=item.title,
                    snippet=item.description,
                    query=query,
                    domain=self._domain(item.link),
                    workflow_hint=self._workflow_hint(raw_text),
                    pain_hint=self._pain_hint(raw_text),
                    metadata_json={"query": query},
                )
                signal_ids.append(event.id)
                problem_signals.append(
                    problem_signal_repo.create(
                        signal_event_id=event.id,
                        canonical_problem_phrase=self._canonical_problem_phrase(raw_text),
                        persona=self._persona_hint(raw_text),
                        workflow=self._workflow_hint(raw_text),
                        pain_type=self._pain_hint(raw_text),
                        urgency_score=self._urgency_score(raw_text),
                        repetition_score=self._repetition_score(raw_text),
                        operational_friction_score=self._friction_score(raw_text),
                        evidence_strength_score=0.6,
                        metadata_json={"query": query, "source": "naver_search"},
                    )
                )
            for item in google_response.items[:2]:
                raw_text = " ".join(part for part in [item.title or "", item.snippet or "", query] if part)
                event = signal_repo.create(
                    source_type="google_search",
                    source_key=query,
                    raw_text=raw_text,
                    normalized_text=self._normalize(raw_text),
                    url=item.link,
                    title=item.title,
                    snippet=item.snippet,
                    query=query,
                    domain=self._domain(item.link),
                    workflow_hint=self._workflow_hint(raw_text),
                    pain_hint=self._pain_hint(raw_text),
                    metadata_json={"query": query},
                )
                signal_ids.append(event.id)
                problem_signals.append(
                    problem_signal_repo.create(
                        signal_event_id=event.id,
                        canonical_problem_phrase=self._canonical_problem_phrase(raw_text),
                        persona=self._persona_hint(raw_text),
                        workflow=self._workflow_hint(raw_text),
                        pain_type=self._pain_hint(raw_text),
                        urgency_score=self._urgency_score(raw_text),
                        repetition_score=self._repetition_score(raw_text),
                        operational_friction_score=self._friction_score(raw_text),
                        evidence_strength_score=0.7,
                        metadata_json={"query": query, "source": "google_search"},
                    )
                )

        grouped: dict[str, list] = defaultdict(list)
        for item in problem_signals:
            key = f"{item.workflow or 'workflow'}::{item.pain_type or 'pain'}"
            grouped[key].append(item)

        created_clusters = []
        scored_ideas = []
        recent_texts = self._recent_report_texts(session)
        for _, members in grouped.items():
            representative = members[0]
            queries = list({member.metadata_json.get('query') for member in members if member.metadata_json and member.metadata_json.get('query')})
            cluster = cluster_repo.create(
                canonical_name=representative.canonical_problem_phrase[:255],
                persona=representative.persona,
                workflow=representative.workflow,
                pain_summary=representative.canonical_problem_phrase,
                representative_queries_json=queries[:6],
                cluster_size=len(members),
                semantic_centroid_text=" ".join(m.canonical_problem_phrase for m in members)[:1000],
                metadata_json={"member_count": len(members)},
            )
            created_clusters.append(cluster)
            for member in members:
                member_repo.create(problem_cluster_id=cluster.id, problem_signal_id=member.id, similarity_score=0.9)

            niche_name = representative.canonical_problem_phrase[:120]
            persona = representative.persona or "소규모 운영자"
            job = f"{cluster.workflow or '운영'} 과정에서 반복 문제를 빠르게 처리하고 싶다"
            pain_summary = cluster.pain_summary or representative.canonical_problem_phrase
            product_wedge = self._product_wedge(cluster.workflow or "운영", cluster.pain_summary or "문제")
            mvp = [
                "문제 사례를 접수하는 간단한 폼",
                "운영자가 수작업으로 처리할 수 있는 백오피스",
                "반자동 알림/분류/우선순위 기능",
            ]
            gtm = [
                "롱테일 검색 랜딩페이지",
                "업종 커뮤니티 사례 공유",
                "수작업 대행형 초기 온보딩",
            ]
            idea = idea_repo.create(
                problem_cluster_id=cluster.id,
                niche_name=niche_name,
                persona=persona,
                job_to_be_done=job,
                pain_summary=pain_summary,
                product_wedge=product_wedge,
                mvp_idea_json=mvp,
                go_to_market_json=gtm,
                novelty_hash=self._normalize(niche_name),
            )

            pricing = self.pricing_evidence_service.collect(canonical_name=niche_name, queries=queries or [niche_name])
            public_data = self.public_data_opportunity_service.analyze(
                canonical_name=niche_name,
                persona=persona,
                problem_summary=pain_summary,
                query_group=queries or [niche_name],
                risk_flags=[],
            )
            evidence_confidence = min(1.0, 0.45 + (0.1 * min(4, len(queries))) + (0.15 if pricing.pricing_page_count else 0))
            evidence_repo.create(
                idea_candidate_id=idea.id,
                search_evidence_json={"queries": queries},
                pricing_evidence_json=pricing.model_dump(mode="json"),
                public_data_evidence_json=(public_data.model_dump(mode="json") if public_data is not None else None),
                confidence_score=evidence_confidence,
            )

            breakdown = self._score_idea(
                niche_name=niche_name,
                persona=persona,
                pain_summary=pain_summary,
                workflow=cluster.workflow or "운영",
                queries=queries or [niche_name],
                cluster_size=len(members),
                pricing_page_count=pricing.pricing_page_count,
                median_price=pricing.median_monthly_price_krw,
                recent_texts=recent_texts,
            )
            score_repo.create(idea_candidate_id=idea.id, **breakdown.model_dump())
            scored_ideas.append((breakdown.final_score, niche_name, persona, pain_summary, breakdown))

        session.commit()
        scored_ideas.sort(key=lambda item: item[0], reverse=True)
        top_niche = scored_ideas[0][1] if scored_ideas else None

        if send_telegram and scored_ideas and self.telegram_service.is_configured():
            top = scored_ideas[0]
            _, niche_name, persona, pain_summary, breakdown = top
            message = (
                "[Seedless Brainstorming V2]\n"
                f"Top niche: {niche_name}\n"
                f"Persona: {persona}\n"
                f"Problem: {pain_summary}\n"
                f"Final score: {breakdown.final_score:.2f}\n"
                f"Micro-revenue: {breakdown.micro_revenue_viability_score:.2f}, Manual-first: {breakdown.manual_first_viability_score:.2f}\n"
                f"Marketing: {breakdown.simple_marketing_score:.2f}, Traffic: {breakdown.guaranteed_traffic_score:.2f}, SEO: {breakdown.seo_advantage_score:.2f}"
            )
            self.telegram_service.send_message(message)

        return SeedlessRunSummary(
            signals=len(signal_ids),
            clusters=len(created_clusters),
            ideas=len(scored_ideas),
            top_niche=top_niche,
        )

    def _score_idea(
        self,
        *,
        niche_name: str,
        persona: str,
        pain_summary: str,
        workflow: str,
        queries: list[str],
        cluster_size: int,
        pricing_page_count: int,
        median_price: int | None,
        recent_texts: list[str],
    ) -> IdeaScoreV2Breakdown:
        demand_score = min(1.0, 0.35 + (0.08 * min(cluster_size, 5)) + (0.05 * min(len(queries), 4)))
        payability_score = 0.55 if pricing_page_count else 0.35
        if median_price and median_price >= 30000:
            payability_score += 0.15
        feasibility_score = 0.72 if any(t in pain_summary for t in ["예약", "정산", "리마인드", "관리", "추적"]) else 0.52
        market_size_score = 0.45
        competition_whitespace_score = 0.62 if pricing_page_count <= 2 else 0.45
        novelty_score = self._novelty_score(niche_name, persona, pain_summary, recent_texts)
        diversity_score = 0.7 if not any(token in niche_name for token in ["미용실"]) else 0.45
        micro_revenue_viability_score = 0.8 if any(token in pain_summary for token in ["예약", "취소", "정산", "자료", "리마인드"]) else 0.5
        manual_first_viability_score = 0.82 if any(token in pain_summary for token in ["연락", "정리", "분류", "추적", "확인"]) else 0.48
        simple_marketing_score = 0.8 if len(niche_name) <= 30 and any(token in niche_name for token in ["관리", "자동화", "알림", "정리"]) else 0.55
        guaranteed_traffic_score = 0.78 if any(token in niche_name for token in ["미용실", "학원", "병원", "스마트스토어", "세무사"]) else 0.5
        seo_advantage_score = 0.76 if len(queries) >= 2 else 0.5
        final_score = (
            demand_score * 0.14
            + payability_score * 0.14
            + feasibility_score * 0.08
            + market_size_score * 0.05
            + competition_whitespace_score * 0.07
            + novelty_score * 0.05
            + diversity_score * 0.05
            + micro_revenue_viability_score * 0.06
            + manual_first_viability_score * 0.06
            + simple_marketing_score * 0.05
            + guaranteed_traffic_score * 0.04
            + seo_advantage_score * 0.04
        ) * 100
        return IdeaScoreV2Breakdown(
            demand_score=round(demand_score, 4),
            payability_score=round(payability_score, 4),
            feasibility_score=round(feasibility_score, 4),
            market_size_score=round(market_size_score, 4),
            competition_whitespace_score=round(competition_whitespace_score, 4),
            novelty_score=round(novelty_score, 4),
            diversity_score=round(diversity_score, 4),
            micro_revenue_viability_score=round(micro_revenue_viability_score, 4),
            manual_first_viability_score=round(manual_first_viability_score, 4),
            simple_marketing_score=round(simple_marketing_score, 4),
            guaranteed_traffic_score=round(guaranteed_traffic_score, 4),
            seo_advantage_score=round(seo_advantage_score, 4),
            final_score=round(final_score, 2),
            reasoning_json={
                "queries": queries,
                "workflow": workflow,
                "cluster_size": cluster_size,
                "median_price": median_price,
            },
        )

    def _recent_report_texts(self, session: Session) -> list[str]:
        rows = session.execute(text("SELECT report_json FROM final_reports ORDER BY created_at DESC LIMIT 20")).fetchall()
        texts = []
        for row in rows:
            payload = row[0]
            if isinstance(payload, str):
                texts.append(payload)
            elif isinstance(payload, dict):
                texts.append(" ".join(str(v) for v in payload.values() if isinstance(v, (str, int, float))))
        return texts

    def _novelty_score(self, niche_name: str, persona: str, pain_summary: str, recent_texts: list[str]) -> float:
        current = set(TOKEN_RE.findall(f"{niche_name} {persona} {pain_summary}".lower()))
        if not recent_texts or not current:
            return 0.8
        best_overlap = 0.0
        for text in recent_texts:
            tokens = set(TOKEN_RE.findall(text.lower()))
            if not tokens:
                continue
            overlap = len(current & tokens) / max(1, len(current | tokens))
            best_overlap = max(best_overlap, overlap)
        return max(0.1, 1.0 - best_overlap)

    def _normalize(self, text: str) -> str:
        return " ".join(TOKEN_RE.findall((text or "").lower()))

    def _domain(self, link: str | None) -> str | None:
        if not link or "://" not in link:
            return None
        return link.split("://", 1)[1].split("/", 1)[0].lower()

    def _workflow_hint(self, text: str) -> str:
        text = text.lower()
        if any(token in text for token in ["예약", "보강", "노쇼", "취소"]):
            return "예약 운영"
        if any(token in text for token in ["정산", "수당", "입금", "청구"]):
            return "정산 운영"
        if any(token in text for token in ["자료", "요청", "서류", "문서"]):
            return "문서 처리"
        if any(token in text for token in ["재고", "발주", "소모품"]):
            return "재고 운영"
        return "운영 관리"

    def _pain_hint(self, text: str) -> str:
        text = text.lower()
        if any(token in text for token in ["누락", "놓친", "실수"]):
            return "누락 위험"
        if any(token in text for token in ["노쇼", "취소", "빈시간"]):
            return "취소 손실"
        if any(token in text for token in ["헷갈", "복잡", "정리"]):
            return "수기 복잡도"
        if any(token in text for token in ["느리", "번거", "일일이"]):
            return "수작업 부담"
        return "운영 비효율"

    def _persona_hint(self, text: str) -> str:
        text = text.lower()
        if "미용실" in text:
            return "소형 미용실 원장"
        if "학원" in text:
            return "소형 학원 원장"
        if "병원" in text:
            return "병원 상담 운영자"
        if "세무사" in text:
            return "세무사 사무소 실무자"
        if "스마트스토어" in text:
            return "소형 스마트스토어 셀러"
        return "소규모 운영자"

    def _canonical_problem_phrase(self, text: str) -> str:
        workflow = self._workflow_hint(text)
        pain = self._pain_hint(text)
        persona = self._persona_hint(text)
        return f"{persona}의 {workflow} 중 {pain} 해결"

    def _urgency_score(self, text: str) -> float:
        return 0.8 if any(token in text for token in ["노쇼", "당일", "누락", "손실"]) else 0.55

    def _repetition_score(self, text: str) -> float:
        return 0.78 if any(token in text for token in ["예약", "일정", "정산", "관리", "리마인드"]) else 0.52

    def _friction_score(self, text: str) -> float:
        return 0.82 if any(token in text for token in ["카톡", "전화", "엑셀", "수기", "일일이"]) else 0.58

    def _product_wedge(self, workflow: str, pain_summary: str) -> str:
        return f"{workflow}에서 '{pain_summary}'만 먼저 해결하는 manual-first + 반자동 운영 도구"
