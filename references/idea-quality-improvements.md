# Micro Niche SaaS 아이디어 품질 개선안

작성일: 2026-04-10

이 문서는 현재 `micro-niche-finder` 프로젝트가 더 좋은 micro niche market SaaS 아이디어를 도출하기 위해 개선하면 좋은 지점을 정리한다.

현재 구조는 대체로 다음 흐름이다.

1. LLM이 seed category에서 후보 아이디어를 생성한다.
2. 후보별 검색어를 확장하고 query group을 만든다.
3. Naver DataLab, Naver Search, Brave Search, Naver Ads, Shopping Insight, KOSIS, 공공데이터 신호를 수집한다.
4. rule-based scoring으로 후보를 랭킹한다.
5. 상위 후보를 LLM으로 최종 리포트화한다.

이 구조는 이미 좋은 출발점이다. 다음 단계의 핵심은 "더 좋은 프롬프트"보다 "실제 고통 신호 수집, evidence confidence, 구매 가능성 검증, 사람 피드백 루프"를 강화하는 것이다.

## 1. 아이디어 생성 전에 문제 신호를 먼저 수집

현재 메인 파이프라인은 seed에서 LLM 후보를 먼저 만들고 나중에 검증한다. 이 방식은 그럴듯한 아이디어는 잘 만들지만, 실제 operator pain에서 출발하지 않은 아이디어가 섞일 수 있다.

개선 방향:

- 네이버 카페, 블로그, 지식iN, 검색 결과 snippet, 커뮤니티 글 제목, 경쟁 서비스 후기, 채용공고, 협회/지원사업 자료에서 반복 불편 문장을 먼저 수집한다.
- LLM은 아이디어 생성기가 아니라 `pain extractor`로 사용한다.
- "누락", "일일이", "엑셀", "카톡", "전화", "정산", "노쇼", "미수금", "자료 요청", "리마인드" 같은 표현을 problem signal로 저장한다.
- problem signal을 clustering한 뒤 SaaS 아이디어로 변환한다.

이미 `SeedlessV2Service`가 이 방향의 초안이다. 다만 현재는 discovery query가 하드코딩되어 있고, 검색 API 실패 시 전체 job이 실패할 수 있다. 이 서비스를 정식 discovery pipeline으로 승격하는 것이 좋다.

## 2. 검색량보다 고통 강도와 구매 가능성을 구조화

좋은 micro niche SaaS는 검색량만으로 결정되지 않는다. 검색량은 작아도 반복 손실, 명확한 구매자, 기존 지출, 낮은 switching cost가 있으면 좋은 후보가 될 수 있다.

추가하면 좋은 평가 항목:

- `quantified_loss`: 월 손실, 시간 손실, 노쇼/미수금/누락 비용
- `current_spend`: 이미 돈을 쓰는 대체재가 있는지
- `workflow_frequency`: 하루/주 몇 번 발생하는지
- `decision_maker_clarity`: 돈 내는 사람이 명확한지
- `manual_service_viability`: 처음에는 사람이 대신 처리해도 되는지
- `switching_cost`: 기존 POS/ERP/CRM 교체 없이 붙일 수 있는지
- `data_dependency_risk`: 네이버/카카오/쿠팡 등 외부 플랫폼 의존도가 큰지
- `support_burden`: CS가 과도하게 무거운지
- `legal_liability`: 의료/세무/법무처럼 책임 리스크가 큰지

현재 candidate schema에는 persona, pain, workaround, payment likelihood는 있지만 정량 손실, 현재 지출, buyer, validation plan이 없다. 이 필드를 추가하면 scoring과 final report 품질이 같이 올라간다.

## 3. Opportunity score와 confidence score를 분리

현재 일부 feature는 근거가 부족해도 중립 이상의 기본값을 갖는다. 예를 들어 시장 ceiling, competitive whitespace 등이 기본적으로 괜찮은 점수로 들어가면 데이터가 없는 후보가 실제보다 좋아 보일 수 있다.

개선 방향:

- `opportunity_score`와 `confidence_score`를 분리한다.
- 데이터가 없으면 점수를 올리지 말고 confidence를 낮춘다.
- 리포트에 "좋아 보이는 이유"와 "아직 모르는 것"을 별도로 출력한다.
- 외부 API 실패 시 mock evidence를 운영 점수에 사용하지 않는다.
- `unknown`은 0.5가 아니라 "검증 필요" 상태로 남긴다.

## 4. Query group 전체를 검증

현재 초기 검색 검증은 대표 query 하나에 의존하는 경향이 있다. 하지만 좋은 문제는 여러 표현으로 검색된다.

예:

- "학원 보강 관리"
- "결석 보강 일정"
- "학부모 카톡 공지"
- "출결 보강표"

이 표현들은 모두 같은 문제를 가리킬 수 있다.

개선 방향:

- query group 전체에 대해 검색 결과를 수집한다.
- query를 의도별로 분리한다.
- 문제 검색, 솔루션 검색, 가격 검색, 커뮤니티 검색, 대체재 검색을 분리한다.
- "문제 검색량"과 "솔루션 검색량"을 따로 계산한다.
- 솔루션 검색은 낮지만 문제 검색이 높으면 좋은 wedge일 수 있다.

## 5. 검색 API 실패를 degraded evidence로 처리

로그상 Brave Search 429로 `seedless_v2`와 `improvement_discovery` job이 실패한 흔적이 있다. 검색 evidence가 자주 실패하면 최종 리포트가 LLM 추정에 과하게 의존하게 된다.

개선 방향:

- Brave/Search API에도 usage counter와 budget allocator를 적용한다.
- 429 발생 시 전체 job 실패가 아니라 해당 source만 `degraded` 처리한다.
- 같은 query는 캐시를 재사용한다.
- 검색 API 호출 전에 중복 query를 제거한다.
- pricing evidence는 비용이 크므로 top 후보에만 후행 실행한다.

## 6. Seedless discovery를 메인 경로로 승격

Seed 기반 파이프라인은 구조가 명확하지만 seed가 좁으면 결과가 반복된다. 실제 로그에서도 미용실 예약/노쇼 계열이 반복된 흔적이 있다.

개선 방향:

- seedless 수집 -> problem signal -> cluster -> idea candidate -> evidence packet -> scoring을 정식 경로로 만든다.
- 하드코딩된 discovery query 대신 자동 query expansion pool을 운영한다.
- 최근 리포트와 유사한 후보는 감점한다.
- 다양한 업종을 강제로 섞는 exploration budget을 둔다.
- 현재 문자열 기반 clustering보다 embedding 기반 clustering을 도입한다.

## 7. 리포트에 검증 액션을 추가

최종 리포트는 현재 niche, MVP, 시장근거, 검색근거, GTM을 설명한다. 여기에 "다음 48시간에 무엇을 검증할지"가 들어가야 실제 의사결정에 더 유용하다.

추가하면 좋은 final report 필드:

- `first_10_leads`: 처음 연락할 대상 유형
- `interview_questions`: 인터뷰 질문 5개
- `smoke_test`: 랜딩페이지/폼/카톡 채널 테스트 방법
- `manual_first_offer`: 자동화 전 수작업 대행 제안
- `price_test`: 월 3만/7만/15만원 중 어떤 가격을 테스트할지
- `kill_criteria`: 버려야 하는 조건
- `mvp_scope`: 반드시 만들 기능과 만들지 않을 기능
- `integration_risk`: 외부 API/플랫폼 의존성

## 8. 경쟁 분석을 "있다/없다"가 아니라 "빈틈"으로 바꾸기

경쟁자가 없는 시장보다 더 좋은 경우는 기존 대안이 너무 크거나, 비싸거나, 특정 workflow를 못 푸는 경우다.

추가하면 좋은 competitive whitespace 신호:

- 기존 솔루션이 all-in-one인지
- 가격이 solo operator에게 높은지
- 특정 업종 언어를 못 쓰는지
- 모바일/Kakao 중심 workflow를 못 푸는지
- 초기 세팅이 무거운지
- 리뷰에서 반복 불만이 있는지

## 9. 시장 크기를 작을수록 좋다고만 보지 않기

Solo founder 관점에서는 작은 시장이 좋을 수 있지만, 너무 작으면 월 100만 원도 어렵다.

추가할 시장성 지표:

- `beachhead_size_score`: 첫 시장이 충분히 작은가
- `micro_revenue_viability`: 100명 x 월 5만 원이 가능한가
- `expansion_path`: 같은 workflow가 인접 업종으로 확장 가능한가
- `reachable_market_score`: 온라인/리스트/커뮤니티로 실제 도달 가능한가

## 10. 사람의 판단을 학습 데이터로 남기기

좋은 아이디어의 기준은 실제로 사람이 보고 판단하면서 바뀐다. 현재 rule-based scoring은 유지하되, 사람 피드백을 저장해 scoring weight를 조정할 수 있어야 한다.

추가하면 좋은 테이블:

- `idea_reviews`
- `label`: good / maybe / bad / duplicate / too_broad / no_buyer / hard_gtm
- `reviewer_notes`
- `interviewed_count`
- `positive_reply_count`
- `landing_page_conversion`
- `paid_pilot_count`

이 데이터를 쌓으면 프로젝트가 점점 "내 기준의 좋은 아이디어"를 더 잘 찾게 된다.

## 가장 먼저 할 3가지

1. Brave/Search 429와 캐싱을 고친다. 자동 discovery가 실패하면 evidence 기반 개선이 막힌다.
2. `ProblemCandidateGenerated`와 `FinalAnalysisOutput`에 `buyer`, `quantified_loss`, `current_spend`, `manual_first_plan`, `validation_plan`, `kill_criteria`를 추가한다.
3. `SeedlessV2Service`를 하드코딩 query 기반 prototype에서 problem-signal 수집 파이프라인으로 확장한다.

## 결론

현재 프로젝트는 기본 구조가 좋다. 다음 개선의 핵심은 LLM 생성 능력을 더 키우는 것이 아니라, 실제 고통 신호를 더 많이 모으고, 근거의 신뢰도를 분리하고, 구매 가능성을 더 직접적으로 검증하고, 사람의 판단을 feedback loop로 저장하는 것이다.

