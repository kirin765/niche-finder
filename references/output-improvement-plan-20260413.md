# 한국 시장 Micro Niche SaaS 결과물 개선안

작성일: 2026-04-13

이 문서는 `micro-niche-finder` 프로젝트의 현재 결과물을 더 날카롭고, 더 검증 가능하고, 더 실행 가능한 형태로 개선하기 위한 우선순위 제안을 정리한다.

핵심 결론은 단순하다.

- 더 많은 아이디어가 필요한 것이 아니다.
- 더 그럴듯한 프롬프트가 필요한 것도 아니다.
- 지금 가장 필요한 것은 `근거의 진실성`, `점수와 신뢰도의 분리`, `검증 액션 중심 리포트`다.

## 현재 상태 요약

프로젝트는 이미 다음 구조를 갖고 있다.

1. seed category 기반 후보 생성
2. query expansion / clustering
3. Naver DataLab, Naver Search, Brave Search, Naver Ads, Shopping Insight, KOSIS, 공공데이터 기반 근거 수집
4. rule-based scoring
5. 최종 리포트 생성

이 구조는 충분히 쓸 만하다. 문제는 "아이디어가 안 나온다"가 아니라, 아래 문제가 결과물 품질을 낮추고 있다는 점이다.

## 가장 큰 문제

## 1. 검색 API 실패 시 운영 점수에 가짜 근거가 섞일 수 있다

현재 Brave 검색 계열은 설정이 없거나 일부 오류 상태에서 mock response를 반환할 수 있다.

관련 코드:

- [google_search_service.py](/root/niche-finder/src/micro_niche_finder/services/google_search_service.py#L28)
- [google_search_service.py](/root/niche-finder/src/micro_niche_finder/services/google_search_service.py#L54)
- [pricing_evidence_service.py](/root/niche-finder/src/micro_niche_finder/services/pricing_evidence_service.py#L19)

이 구조의 문제는 다음과 같다.

- 검색이 실패해도 "검색 결과가 존재하는 것처럼" downstream이 해석할 수 있다.
- pricing evidence도 같은 검색 결과를 재사용하므로 가격 근거까지 오염될 수 있다.
- 결과적으로 실제 근거가 약한 후보가 생각보다 좋아 보인다.

## 2. 근거가 없을 때도 feature 기본값이 중립 이상으로 들어간다

관련 코드:

- [feature_service.py](/root/niche-finder/src/micro_niche_finder/services/feature_service.py#L20)

DataLab 값이 없을 때도 다음 값들이 기본으로 들어간다.

- `absolute_demand_score = 0.4`
- `payability_score = 0.5`
- `market_size_ceiling_score = 0.7`
- `competitive_whitespace_score = 0.6`

이 방식은 "모름"을 "중간 이상"으로 처리하는 셈이다.

문제가 되는 이유:

- 근거 부족 후보가 덜 불리해진다.
- 검색/수요 데이터가 비어도 기회 점수가 유지된다.
- LLM 리포트가 실제보다 자신감 있게 말하게 된다.

## 3. opportunity score와 confidence score가 분리되어 있지 않다

관련 코드:

- [scoring_service.py](/root/niche-finder/src/micro_niche_finder/services/scoring_service.py#L29)
- [schemas.py](/root/niche-finder/src/micro_niche_finder/domain/schemas.py#L448)

현재는 사실상 하나의 점수 체계만 있다.

이 구조에서는 아래 두 경우가 구분되지 않는다.

- 근거가 충분해서 진짜 좋은 후보
- 근거는 약하지만 휴리스틱상 괜찮아 보이는 후보

즉, 결과물의 "기회도"와 "확신도"가 섞여 있다.

## 4. 대표 query 하나에 너무 많이 의존한다

관련 코드:

- [pipeline.py](/root/niche-finder/src/micro_niche_finder/jobs/pipeline.py#L227)
- [pipeline.py](/root/niche-finder/src/micro_niche_finder/jobs/pipeline.py#L279)

현재 Naver Search / Brave Search 초기 검증은 `group.queries[0]` 중심이다.

하지만 좋은 micro niche 문제는 같은 pain이 여러 표현으로 퍼져 있다.

예:

- 학원 보강 관리
- 결석 보강 일정
- 출결 보강표
- 학부모 카톡 공지

이들을 하나의 문제군으로 보지 못하면 실제 수요를 과소 혹은 과대평가하게 된다.

## 5. 리포트 생성 기준이 너무 관대하다

관련 코드:

- [pipeline.py](/root/niche-finder/src/micro_niche_finder/jobs/pipeline.py#L558)

현재는 상위 `top_k`면 거의 그대로 리포트가 생성된다.

문제:

- 최저 점수 threshold가 없다.
- confidence threshold가 없다.
- "탐색 가치 있음"과 "바로 검증할 가치 있음"이 구분되지 않는다.

실무적으로는 다음 3단계가 분리되어야 한다.

1. 아이디어로 보관할 후보
2. 인터뷰할 후보
3. 랜딩/결제 테스트할 후보

## 6. seedless discovery는 아직 prototype 수준이다

관련 코드:

- [seedless_v2_service.py](/root/niche-finder/src/micro_niche_finder/services/seedless_v2_service.py#L35)
- [seedless_v2_service.py](/root/niche-finder/src/micro_niche_finder/services/seedless_v2_service.py#L139)

현재 seedless V2는 다음 한계가 있다.

- discovery query가 하드코딩
- 검색 API 실패에 취약
- 문자열 기반 grouping
- 업종 다양성 제어 부족

즉, 방향은 맞지만 아직 메인 discovery 엔진으로 쓰기에는 거칠다.

## 7. 최종 리포트가 설명 중심이고 검증 중심이 아니다

관련 코드:

- [schemas.py](/root/niche-finder/src/micro_niche_finder/domain/schemas.py#L481)

현재 리포트는 niche, MVP, GTM 설명은 가능하다. 하지만 아래가 없다.

- 누가 돈 내는지
- 어떤 손실을 줄이는지
- 48시간 안에 무엇을 검증할지
- 어떤 조건이면 버려야 하는지

이 상태에서는 "좋아 보이는 보고서"는 만들지만 "실행 가능한 의사결정 문서"는 되기 어렵다.

## 개선 우선순위

## 1순위: 가짜 근거 제거 + degraded evidence 처리

목표:

- mock response를 운영 scoring path에서 제외
- 429/401/403/timeout을 `degraded` 상태로 기록
- source failure가 전체 잡 실패로 번지지 않게 처리
- cache와 dedupe로 검색 API 낭비를 줄임

필수 작업:

1. search/pricing context에 `evidence_status` 추가
2. mock response는 테스트 경로에서만 사용
3. runtime failure 시 `unavailable` 또는 `degraded`로 명시
4. same query cache 도입
5. pricing evidence는 top 후보 후행 실행

기대 효과:

- 결과물의 신뢰도가 즉시 올라간다.
- 리포트가 추측과 근거를 덜 혼동한다.
- Brave 429 반복 문제의 운영 영향이 줄어든다.

## 2순위: opportunity score와 confidence score 분리

목표:

- "좋아 보이는 정도"와 "그 판단을 얼마나 믿을 수 있는지"를 분리

권장 구조:

- `opportunity_score`
- `confidence_score`
- `evidence_coverage`
- `unknown_fields`

운영 규칙 예시:

- `confidence_score < 0.45` 이면 `recommended_priority` 상한 제한
- `confidence_score < 0.35` 이면 full report 대신 검증 대기 상태로 저장
- unknown이 많으면 점수를 올리지 말고 confidence만 낮춤

기대 효과:

- 약한 근거 후보가 상위권을 차지하는 문제를 줄일 수 있다.
- 보고서가 과신하지 않게 된다.

## 3순위: candidate / report schema 확장

현재 `ProblemCandidateGenerated`에는 buyer, 손실, current spend 같은 핵심 필드가 없다.

관련 코드:

- [schemas.py](/root/niche-finder/src/micro_niche_finder/domain/schemas.py#L43)
- [schemas.py](/root/niche-finder/src/micro_niche_finder/domain/schemas.py#L464)
- [schemas.py](/root/niche-finder/src/micro_niche_finder/domain/schemas.py#L481)

추가 권장 필드:

- `buyer`
- `quantified_loss`
- `current_spend`
- `workflow_frequency_detail`
- `decision_maker_clarity`
- `switching_cost`
- `manual_first_plan`
- `validation_plan`
- `kill_criteria`
- `integration_risk`

리포트 추가 필드:

- `first_10_leads`
- `interview_questions`
- `smoke_test`
- `price_test`
- `must_have_scope`
- `must_not_build_scope`

기대 효과:

- 보고서가 설명서에서 실행계획서로 바뀐다.
- 실제 인터뷰와 MVP 검증에 바로 연결된다.

## 4순위: query group 전체 검증

목표:

- 대표 query 하나가 아니라 문제군 전체를 검증

권장 방식:

1. query를 의도별로 분리
2. 문제 검색 / 솔루션 검색 / 가격 검색 / 커뮤니티 검색 / 대체재 검색을 따로 수집
3. group coverage score 계산
4. "문제 검색량 > 솔루션 검색량" 패턴을 별도 가점

기대 효과:

- 같은 pain의 여러 표현을 제대로 묶을 수 있다.
- niche wedge 탐지가 더 정밀해진다.

## 5순위: seedless discovery를 정식 메인 경로로 승격

목표:

- seed 기반 생성보다 실제 pain signal 기반 수집을 우선

권장 수집원:

- 네이버 블로그
- 지식iN
- 카페 / 커뮤니티 글 제목
- 검색 결과 snippet
- 경쟁 제품 리뷰
- 채용공고
- 협회/지원사업 문서

권장 방식:

1. raw text 수집
2. pain phrase extraction
3. clustering
4. candidate synthesis
5. evidence packet 생성
6. scoring

추가 개선:

- hardcoded query 제거
- exploration budget으로 업종 다양성 확보
- recent report similarity penalty 추가
- embedding clustering 도입

기대 효과:

- 반복되는 업종 편향이 줄어든다.
- 실제 현장 pain에 더 가깝게 접근한다.

## 6순위: 사람 피드백 루프 저장

좋은 아이디어의 기준은 실제로 사람 판단을 거치며 정교해진다.

권장 테이블:

- `idea_reviews`

권장 컬럼:

- `label`
- `reviewer_notes`
- `interviewed_count`
- `positive_reply_count`
- `landing_page_conversion`
- `paid_pilot_count`

label 예시:

- `good`
- `maybe`
- `bad`
- `duplicate`
- `too_broad`
- `no_buyer`
- `hard_gtm`

기대 효과:

- scoring weight 조정 근거가 생긴다.
- 프로젝트가 "내 기준의 좋은 아이디어"를 학습하게 된다.

## 바로 실행할 3가지

1. `mock evidence 제거 + degraded handling + cache`
2. `confidence score 도입 + report threshold`
3. `schema 확장 + validation 중심 report 필드 추가`

## 추천 구현 순서

### Phase 1

- search/pricing evidence status 추가
- mock response를 scoring path에서 제외
- report gating 추가

### Phase 2

- candidate / final report schema 확장
- validation plan / kill criteria / buyer / quantified loss 반영

### Phase 3

- seedless discovery 메인화
- query group multi-intent validation
- feedback loop 저장

## 최종 정리

이 프로젝트의 다음 개선 포인트는 LLM을 더 똑똑하게 만드는 것이 아니다.

진짜 필요한 것은 아래 세 가지다.

- 근거가 없는 경우 솔직하게 모른다고 말하는 시스템
- 좋아 보이는 후보와 믿을 수 있는 후보를 분리하는 시스템
- 보고서가 끝이 아니라 인터뷰와 결제 검증으로 이어지는 시스템

이 세 가지가 정리되면 결과물의 품질은 단순한 "아이디어 리스트"에서 "실제로 선택 가능한 niche thesis" 수준으로 올라간다.
