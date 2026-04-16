# Micro Niche Finder

Korean-market **micro niche SaaS discovery system** for a **solo founder**.

The project does not try to find every trending keyword. It tries to find **small, repeated, painful, software-solvable workflows** that a 1-person builder can ship as a narrow SaaS wedge in weeks, not months.

The discovery scope is intentionally limited to **vertical markets** tied to specific industries and operator segments, not horizontal software categories.

## Detailed goal

This project is optimized for questions like:

- Which Korean small-business operators are still managing a repeated workflow with **Excel, KakaoTalk, phone calls, reminders, and manual checking**?
- Which niche is **narrow enough** for a solo founder to ship first?
- Which niche has enough evidence from **trend signals, search evidence, shopping behavior, market structure, and public data** to justify further interviews or MVP work?

The target output is **not** a generic “big market idea”.

The target output is a ranked list of candidates like:

- a small clinic or counseling center workflow
- a seller operations workflow
- a reservation / reminder / reconciliation / inquiry-loss-prevention workflow
- a narrow compliance or back-office workflow backed by structured data

## What the system is trying to optimize

The ranking logic intentionally favors:

- **1-5 person teams**
- **owner-operator businesses**
- **high-frequency operational pain**
- **manual workaround-heavy workflows**
- **narrow MVP wedges**
- **lightweight integrations**

It intentionally avoids or penalizes:

- broad ERP / CRM / POS replacement
- enterprise-wide systems
- one-off consumer curiosity
- trend spikes with weak operating pain
- regulated domains that become too heavy for a solo founder

## High-level architecture

The system combines:

1. **LLM generation** to propose candidate pains and expand queries
2. **Naver DataLab** to measure relative trend behavior
3. **Naver Search / Google Search** to inspect search evidence and existing solutions
4. **Naver Shopping Insight** for commerce/product/seller niches only
5. **KOSIS** for optional market-size reference context
6. **Selected data.go.kr datasets** to judge fragmentation, seller growth, business validation, and narrow compliance workflows
7. **Rule-based scoring** tuned for solo-founder-friendly SaaS wedges
8. **Final report generation** that explains the niche, MVP angle, risks, and go-to-market path

## Main workflow

The core pipeline lives in `src/micro_niche_finder/jobs/pipeline.py`.

### Pipeline steps

1. **Seed selection**
   - Input starts from a seed category such as `스마트스토어 운영`, `학원 운영`, or `식당 운영`.

2. **Candidate generation**
   - The LLM generates repeated operational pain points for that seed.
   - Each candidate includes persona, pain, workaround, payment likelihood, software fit, and search-ready query ideas.

3. **Query expansion**
   - The LLM expands each candidate into Korean queries that can be used for trend/search collection.

4. **Query clustering**
   - Expanded queries are normalized into a canonical niche name and grouped into a query group.

5. **Initial evidence collection**
   - Naver DataLab baseline trend data is fetched.
   - Naver Search evidence is fetched for the first representative query.
   - Naver Shopping Insight is fetched only if the niche looks commerce/product/seller-related.
   - KOSIS market-size context is fetched if KOSIS is fully configured.
   - Public data opportunity context is generated from known data.go.kr datasets.

6. **Feature extraction**
   - Trend features such as growth, volatility, spike ratio, segment consistency, commercial intent, and specificity are computed.

7. **Scoring**
   - Candidates are scored with a rule-based scorer that prefers narrow, repeated, operator-facing workflows.

8. **Final report generation**
   - The top candidates are turned into human-readable reports with:
     - niche summary
     - MVP idea
     - go-to-market suggestions
     - landing-page positioning hook
     - first 10 lead targets
     - interview questions / validation plan
     - manual-first offer and pricing test
     - market-size summary
     - search evidence summary
     - shopping evidence summary
     - public data summary
     - risk flags

## Evidence sources and how they are used

### 1. OpenAI Responses API

Used for:

- seed generation
- candidate generation
- query expansion
- KOSIS industry mapping
- Naver Shopping category mapping
- final report generation

The OpenAI integration uses **structured JSON schema outputs**.

### 2. Naver DataLab Search API

Used as the **primary trend signal source**.

It helps answer:

- Is this query group still being searched?
- Is it growing or decaying?
- Is it a stable pain or just a spike?
- Is the demand segmented by age, gender, or device?

Important note:

- DataLab is treated as **relative trend evidence**, not absolute demand.

### 3. Naver Search API

Used as **search evidence / category evidence**.

It helps answer:

- Are people actively searching for the workflow?
- Are there already niche tools or workaround posts?
- Is the category already crowded with obvious competitors?

### 4. Brave Search API

Used as an optional supplementary evidence source for broader web validation outside Naver-heavy surfaces.

It is helpful when:

- relevant evidence is outside Naver-heavy surfaces
- the niche overlaps with broader web or SaaS patterns
- competitor and content evidence should be cross-checked against a non-Naver index

Brave usage is capped at `BRAVE_SEARCH_MONTHLY_LIMIT` calls per month. The default is `1000`.

### 5. Naver Shopping Insight API

Used **selectively**, not globally.

It is useful for:

- Smartstore / seller operations
- product-category workflows
- commerce / retail / shopping-adjacent niches

It is intentionally ignored for:

- most pure B2B operational workflows
- reservations, counseling, scheduling, or back-office niches with no product-buying behavior

### 6. KOSIS OpenAPI

Used as **optional market-size reference context**.

Current implementation supports:

- legacy single employee-count mode
- profile-based structure / revenue / growth / regional summaries when `KOSIS_PROFILE_OPTIONS_JSON` is configured

It is intended to answer:

- Is the mapped industry large or small?
- Is this a fragmented or narrow segment?

Important note:

- KOSIS is a supporting context source, not the main ranking source.
- Live KOSIS collection requires full table/item/industry configuration, not just an API key.

### Project-ready KOSIS mapping design

The repository now supports a **profile-based KOSIS mapping layer** while keeping the old single employee-count configuration as a fallback.

That design should support four kinds of signals:

1. **Structure**: business count + employee count
2. **Money**: revenue + value added
3. **Growth**: multi-year CAGR
4. **Demand context**: population / household / consumption trend

#### A. Structure profile

Recommended table:

- `DT_1F2A01` for nationwide business structure

Recommended project interpretation:

- `T1` = business count
- `T2` = employee count

Suggested profile shape:

```json
{
  "name": "business-structure",
  "tbl_id": "DT_1F2A01",
  "classification": "KSIC10",
  "industry_level": "mid",
  "metrics": {
    "business_count": "T1",
    "employee_count": "T2"
  },
  "static_params": {
    "PRD_SE": "A",
    "OBJ_L1": "전산업"
  }
}
```

How to use it:

- **business count high + employee count low** → fragmented small-operator market
- **business count low + employee count low** → narrow niche candidate

#### B. Revenue / value-added profiles

Recommended tables:

- `DT_1SB1501` for service industries
- `DT_1MC1503` for manufacturing industries

Suggested profile shape:

```json
{
  "name": "service-economics",
  "tbl_id": "DT_1SB1501",
  "classification": "KSIC10",
  "industry_level": "mid",
  "metrics": {
    "business_count": "T1",
    "employee_count": "T2",
    "revenue": "T3",
    "value_added": "T4"
  },
  "static_params": {
    "PRD_SE": "A"
  }
}
```

And:

```json
{
  "name": "manufacturing-economics",
  "tbl_id": "DT_1MC1503",
  "classification": "KSIC10",
  "industry_level": "mid",
  "metrics": {
    "employee_count": "T2",
    "revenue": "T3"
  },
  "static_params": {
    "PRD_SE": "A"
  }
}
```

Core KPI:

- `revenue / employee_count`

Interpretation:

- **low employee count + high revenue per employee** → higher-value niche

#### C. Time-series design

The same structure and revenue tables should support a multi-year range:

```json
{
  "time_range": ["2019", "2020", "2021", "2022", "2023"]
}
```

Recommended calculation:

- `CAGR = (latest / earliest)^(1 / years) - 1`

Suggested filters:

- business CAGR > `0.05`
- employee CAGR > `0.03`

Interpretation:

- small-but-growing segments are stronger niche candidates than flat or shrinking segments

#### D. Demand-context profiles

Recommended demand-side references:

- `DT_1L1A001` for household / consumption context
- `DT_1B040A3` for population structure context

Suggested profile shapes:

```json
{
  "name": "single-household-consumption",
  "tbl_id": "DT_1L1A001",
  "dimension": "소비항목",
  "static_params": {
    "가구유형": "1인가구"
  }
}
```

```json
{
  "name": "population-structure",
  "tbl_id": "DT_1B040A3",
  "static_params": {}
}
```

Project interpretation examples:

- aging growth → healthcare / care / clinic-adjacent workflows
- 1-person household growth → food / appliance / convenience categories
- youth decline → weaker education-related demand

#### E. Region design

Structure table can also be reused for regional concentration analysis:

```json
{
  "name": "regional-business-structure",
  "tbl_id": "DT_1F2A01",
  "static_params": {
    "지역": "시군구"
  }
}
```

Core regional KPI:

- `regional share / national average share`

Interpretation:

- if concentration > `1.5`, the niche may be regionally concentrated enough for focused B2B targeting

#### F. Industry-code mapping design

The project should not rely only on broad one-off industry labels.

Recommended mapping shape:

```json
{
  "mapping": {
    "스마트스토어": "G47912",
    "온라인교육": "P85659",
    "헬스케어": "Q86",
    "1인가구식품": "C107",
    "물류자동화": "H52"
  }
}
```

Recommended LLM role:

1. map candidate niche to KSIC-like industry codes
2. choose which KOSIS profile group applies
3. compute structure / revenue / growth / demand subscores
4. return top-ranked segments for report use

#### G. Recommended integrated config shape

This is the project-level JSON design that best matches the future refactor:

```json
{
  "data_sources": [
    {
      "name": "business-structure",
      "tbl_id": "DT_1F2A01"
    },
    {
      "name": "service-revenue",
      "tbl_id": "DT_1SB1501"
    },
    {
      "name": "manufacturing-revenue",
      "tbl_id": "DT_1MC1503"
    }
  ],
  "metrics": {
    "employee": "T2",
    "revenue": "T3"
  },
  "filters": {
    "employee_max": 50,
    "cagr_min": 0.05
  }
}
```

#### H. Practical note for this repository

Today the code still accepts these legacy single-profile environment variables:

- `KOSIS_TBL_ID`
- `KOSIS_EMPLOYEE_ITM_ID`
- `KOSIS_INDUSTRY_OPTIONS_JSON`
- `KOSIS_STATIC_PARAMS_JSON`

The preferred new configuration is `KOSIS_PROFILE_OPTIONS_JSON`, but the legacy fields still work.

If you continue refining implementation later, the clean next steps are:

1. introduce a `KOSIS_PROFILE_OPTIONS_JSON` style config
2. support per-profile metric IDs instead of one `KOSIS_EMPLOYEE_ITM_ID`
3. let pipeline/report logic aggregate structure, money, growth, and demand into one KOSIS context
4. keep the current employee-count collector as a backward-compatible fallback

### 7. data.go.kr public data

This project currently uses selected public APIs as **niche interpretation and validation logic**, not yet as full periodic live collectors.

Included datasets:

| Dataset | Purpose in this project | How it helps |
| --- | --- | --- |
| `15012005` 소상공인시장진흥공단 상가(상권)정보 | Fragmentation / local density validation | Useful for offline service niches like clinics, academies, salons, restaurants, brokers |
| `15126322` 공정거래위원회 통신판매사업자 등록현황 통계 | Seller segment size / growth validation | Useful for ecommerce and seller-operation niches |
| `15081808` 국세청 사업자등록정보 진위확인 및 상태조회 | Business verification workflow validation | Useful for onboarding, supplier validation, partner risk checks |
| `15143798` 식품의약품안전처 푸드QR 정보 서비스 | Narrow food/compliance workflow validation | Useful for food labeling / ingredient / allergy data workflows |
| `15057456` 식품의약품안전처 의료기기 품목허가 정보 | Narrow medical-device back-office workflow validation | Useful for regulated catalog / approval-tracking support tools |

Important note:

- Public data is treated as a way to validate **segment structure, fragmentation, onboarding, or compliance workload**.
- It is **not** treated as proof of willingness to pay.

## Scoring philosophy

The scoring engine lives in `src/micro_niche_finder/services/scoring_service.py`.

It considers:

- repeated pain
- problem intensity
- payment likelihood
- persistent signal
- segment focus
- implementation feasibility
- penalties

Specific solo-founder-friendly boosts include:

- manual workaround signal
- narrow operator workflow bonus
- public-data leverage bonus

Specific penalties include:

- enterprise complexity
- high regulation burden
- brand dependency
- spike-heavy / seasonal noise
- broad all-in-one scope

## Current report output

Each final report is designed to answer:

- **What is the niche?**
- **Why now / why this problem?**
- **What should the MVP be?**
- **Can a solo founder realistically build it?**
- **What evidence supports it?**
- **What risks make it weaker than it looks?**

Current evidence summary fields:

- `market_size_summary`
- `search_evidence_summary`
- `shopping_evidence_summary`
- `public_data_summary`

## Repo structure

- `apps/api`: FastAPI app and HTTP routes
- `apps/worker`: worker entrypoints for collection and bootstrap flows
- `src/micro_niche_finder/config`: settings and DB config
- `src/micro_niche_finder/domain`: schemas and enums
- `src/micro_niche_finder/repos`: persistence layer
- `src/micro_niche_finder/services`: API clients, scoring, reporting, evidence logic
- `src/micro_niche_finder/jobs`: pipeline jobs
- `scripts`: bootstrap and operational helper scripts
- `deploy`: Ubuntu and systemd deployment examples
- `tests`: regression and smoke-oriented tests

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL, with SQLite only for tests
- OpenAI Responses API

## Quick start

1. Create a Python 3.12 virtual environment.
2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and fill in credentials.
4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn apps.api.main:app --reload
```

## Core API usage

Create a seed category:

```bash
curl -X POST http://localhost:8000/api/v1/seeds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "스마트스토어 운영",
    "description": "한국 소형 셀러의 반복 업무 탐색"
  }'
```

Run the pipeline:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "seed_category_id": 1,
    "candidate_count": 20,
    "top_k": 10
  }'
```

List reports:

```bash
curl http://localhost:8000/api/v1/reports?limit=10
```

## Automation and periodic collection

### Bootstrap schedules for existing query groups

```bash
python scripts/bootstrap_collection_schedules.py
```

### Auto-generate seed categories and run pipelines

```bash
python -m apps.worker.bootstrap_auto_seeds --seed-count 1 --candidate-count 1 --top-k 1 --evidence-mode minimal --log-detail summary
```

This is the periodic batch entrypoint for automated report generation. It discovers fresh seed categories, runs the pipeline for each seed, and persists the resulting reports. Use `--evidence-mode full` for the richest evidence pass, or `--evidence-mode minimal` for the fastest scheduled run.

### Run one Naver DataLab collector cycle

```bash
python -m apps.worker.run_collector --max-calls 5
```

### Run one Google collector cycle

```bash
python -m apps.worker.run_google_collector --max-calls 3
```

### Run one Naver Search collector cycle

```bash
python -m apps.worker.run_naver_search_collector --max-calls 3
```

### Run one Naver Shopping Insight collector cycle

```bash
python -m apps.worker.run_naver_shopping_insight_collector
```

### Run one KOSIS collector cycle

```bash
python -m apps.worker.run_kosis_collector --max-calls 3
```

## Budgeting model

The periodic collectors do not spend the full daily budget immediately.

Instead:

- each source has a daily limit
- the allocator calculates remaining budget
- the allocator spreads calls over remaining time slots
- only **due schedules** are processed

This means:

- `NAVER_DATALAB_DAILY_LIMIT=1000` is a **cap**, not a guaranteed burn rate
- if there are no query groups or no due schedules, nothing runs
- if a source is not configured, its collector returns a clean no-op summary

## Environment configuration

Main groups of environment variables:

- **OpenAI**
  - `OPENAI_API_KEY`
  - `OPENAI_CANDIDATE_MODEL`
  - `OPENAI_FINAL_MODEL`
- **Brave Search**
  - `BRAVE_SEARCH_API_KEY`
  - `BRAVE_SEARCH_MONTHLY_LIMIT`
- **Naver DataLab**
  - `NAVER_DATALAB_CLIENT_ID`
  - `NAVER_DATALAB_CLIENT_SECRET`
  - `NAVER_DATALAB_DAILY_LIMIT`
- **Naver Search**
  - `NAVER_SEARCH_CLIENT_ID`
  - `NAVER_SEARCH_CLIENT_SECRET`
  - `NAVER_SEARCH_DAILY_LIMIT`
- **Naver Shopping Insight**
  - `NAVER_SHOPPING_INSIGHT_DAILY_LIMIT`
  - `NAVER_SHOPPING_CATEGORY_OPTIONS_JSON`
- **KOSIS**
  - `KOSIS_API_KEY`
  - `KOSIS_TBL_ID`
  - `KOSIS_EMPLOYEE_ITM_ID`
  - `KOSIS_INDUSTRY_OPTIONS_JSON`
  - `KOSIS_PROFILE_OPTIONS_JSON`
- **Collectors**
  - `COLLECTOR_INTERVAL_MINUTES`
  - `COLLECTOR_SCHEDULE_CADENCE_MINUTES`
  - `COLLECTOR_DEFAULT_PRIORITY`
- **Telegram / Gmail**
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `GMAIL_SMTP_HOST`
  - `GMAIL_SMTP_PORT`
  - `GMAIL_USERNAME`
  - `GMAIL_APP_PASSWORD`
  - `GMAIL_FROM_EMAIL`
  - `GMAIL_TO_EMAILS`

See `.env.example` for a fuller example.

## Deployment

Ubuntu deployment instructions and systemd unit examples are in:

- `deploy/ubuntu.md`
- `deploy/systemd/`

## Current limitations

1. **KOSIS is partially integrated**
   - authentication works
   - employee-count collector exists
   - full real-world data collection still depends on table/item/industry configuration

2. **Public data integration is currently interpretation-first**
   - selected data.go.kr datasets are already used to improve scoring/reporting logic
   - most of them are not yet wired as periodic live collectors

3. **Search evidence is not the same as payment evidence**
   - Naver/Google results help validate category existence and language
   - they do not prove conversion by themselves

4. **This system narrows opportunities, it does not replace interviews**
   - the intended next step after a promising report is still founder research, outreach, and lightweight validation

## Testing

Run the full test suite:

```bash
pytest -q
```

The suite covers scoring, API client behavior, structured-output helper behavior, and recent evidence-source integrations.
