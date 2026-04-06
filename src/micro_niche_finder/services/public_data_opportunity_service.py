from __future__ import annotations

from micro_niche_finder.domain.schemas import PublicDataContext, PublicDataRecommendation


class PublicDataOpportunityService:
    def analyze(
        self,
        *,
        canonical_name: str,
        persona: str,
        problem_summary: str,
        query_group: list[str],
        risk_flags: list[str],
    ) -> PublicDataContext | None:
        text = " ".join([canonical_name, persona, problem_summary, *query_group]).lower()
        recommendations: list[PublicDataRecommendation] = []

        if self._has_any(
            text,
            (
                "학원",
                "미용실",
                "피부관리실",
                "식당",
                "카페",
                "네일",
                "필라테스",
                "헬스장",
                "세탁",
                "부동산",
                "인테리어",
                "병원",
                "의원",
            ),
        ):
            recommendations.append(
                PublicDataRecommendation(
                    dataset_id="15012005",
                    source_label="data.go.kr",
                    dataset_name="소상공인시장진흥공단_상가(상권)정보",
                    dataset_url="https://www.data.go.kr/data/15012005/openapi.do",
                    relevance="high",
                    use_case="지역별 점포 밀도와 업종 분포를 봐서 시장 파편화, 현장 영업 가능성, 과밀 여부를 판단한다.",
                    caveat="문제 강도나 구매 의향을 직접 보여주지는 않으므로 검색/커뮤니티 신호와 함께 봐야 한다.",
                )
            )

        if self._has_any(
            text,
            (
                "스마트스토어",
                "쿠팡",
                "셀러",
                "쇼핑몰",
                "통신판매",
                "상품",
                "리뷰",
                "배송",
                "정산",
                "가격",
                "재고",
                "발주",
            ),
        ):
            recommendations.append(
                PublicDataRecommendation(
                    dataset_id="15126322",
                    source_label="data.go.kr",
                    dataset_name="공정거래위원회_통신판매사업자 등록현황 통계 제공 서비스",
                    dataset_url="https://www.data.go.kr/data/15126322/openapi.do",
                    relevance="high",
                    use_case="월별·지역별 통신판매사업자 수로 셀러 세그먼트의 크기와 증가 추세를 확인한다.",
                    caveat="사업자 수 증가는 경쟁 증가일 수도 있으므로 수익성 판단과는 분리해서 해석해야 한다.",
                )
            )

        if self._has_any(
            text,
            (
                "사업자",
                "입점",
                "셀러",
                "거래처",
                "공급사",
                "세금계산서",
                "정산",
                "휴폐업",
                "온보딩",
            ),
        ):
            recommendations.append(
                PublicDataRecommendation(
                    dataset_id="15081808",
                    source_label="data.go.kr",
                    dataset_name="국세청 사업자등록정보 진위확인 및 상태조회 서비스",
                    dataset_url="https://www.data.go.kr/data/15081808/openapi.do",
                    relevance="medium",
                    use_case="거래처·셀러·파트너 온보딩 시 사업자 상태 검증과 휴폐업 체크를 자동화하는 SaaS 웨지에 유용하다.",
                    caveat="시장 수요 신호라기보다 운영 자동화와 리스크 절감 근거에 가깝다.",
                )
            )

        if self._has_any(
            text,
            (
                "식품",
                "푸드",
                "원재료",
                "알레르기",
                "영양",
                "표시",
                "밀키트",
                "간편식",
                "라벨",
            ),
        ):
            recommendations.append(
                PublicDataRecommendation(
                    dataset_id="15143798",
                    source_label="data.go.kr",
                    dataset_name="식품의약품안전처_푸드QR 정보 서비스",
                    dataset_url="https://www.data.go.kr/data/15143798/openapi.do",
                    relevance="medium",
                    use_case="식품 라벨, 원재료, 알레르기, 영양정보 자동 정리나 검수 워크플로 SaaS의 데이터 기반이 될 수 있다.",
                    caveat="규제 해석이 필요한 영역이라 범위를 넓히면 solo founder에게 무거워질 수 있다.",
                )
            )

        if self._has_any(
            text,
            (
                "의료기기",
                "품목허가",
                "허가번호",
                "병원 장비",
                "재활기기",
                "진단기기",
            ),
        ):
            recommendations.append(
                PublicDataRecommendation(
                    dataset_id="15057456",
                    source_label="data.go.kr",
                    dataset_name="식품의약품안전처_의료기기 품목허가 정보",
                    dataset_url="https://www.data.go.kr/data/15057456/openapi.do",
                    relevance="medium",
                    use_case="허가 품목 정리, 카탈로그 업데이트, 대리점·유통사의 품목 확인 자동화처럼 좁은 규제 데이터 업무에 유용하다.",
                    caveat="의료기기 규제는 무겁기 때문에 broad vertical SaaS보다는 백오피스 보조 도구에만 적합하다.",
                )
            )

        if not recommendations:
            return None

        summary = self._build_summary(recommendations, risk_flags)
        return PublicDataContext(summary=summary, recommendations=recommendations[:3])

    def _build_summary(
        self,
        recommendations: list[PublicDataRecommendation],
        risk_flags: list[str],
    ) -> str:
        names = ", ".join(item.dataset_name for item in recommendations[:3])
        if any(item.dataset_id in {"15143798", "15057456"} for item in recommendations):
            if "regulation_risk" in risk_flags:
                return f"{names} 같은 공공데이터로 운영 구조를 검증할 수 있지만, 규제 해석 부담이 있어 좁은 보조 워크플로우로 제한하는 편이 안전하다."
            return f"{names} 같은 공공데이터로 규제/표시 업무의 반복성을 확인할 수 있어, 좁은 컴플라이언스 보조 SaaS 후보를 검증하는 데 도움이 된다."
        if any(item.dataset_id == "15126322" for item in recommendations):
            return f"{names}를 함께 보면 셀러·통신판매 세그먼트의 규모와 증가 흐름, 운영 검증 포인트를 동시에 볼 수 있어 이커머스 운영 SaaS 후보를 더 좁히기 좋다."
        return f"{names}를 활용하면 지역 상권 파편화나 사업자 운영 검증처럼 solo founder가 공략하기 쉬운 세그먼트를 더 구체적으로 좁힐 수 있다."

    def leverage_score(self, *, canonical_name: str, persona: str, problem_summary: str, query_group: list[str]) -> float:
        context = self.analyze(
            canonical_name=canonical_name,
            persona=persona,
            problem_summary=problem_summary,
            query_group=query_group,
            risk_flags=[],
        )
        if context is None:
            return 0.0
        high_count = sum(1 for item in context.recommendations if item.relevance == "high")
        medium_count = sum(1 for item in context.recommendations if item.relevance == "medium")
        return min(1.0, (high_count * 0.45) + (medium_count * 0.2))

    @staticmethod
    def _has_any(text: str, markers: tuple[str, ...]) -> bool:
        return any(marker in text for marker in markers)
