# Ubuntu Operations

## Install

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip build-essential libpq-dev postgresql-client
sudo mkdir -p /opt
cd /opt
sudo git clone git@github.com:kirin765/niche-finder.git micro-niche-finder
sudo chown -R ubuntu:ubuntu /opt/micro-niche-finder
cd /opt/micro-niche-finder
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp deploy/systemd/micro-niche-finder.env.example /etc/micro-niche-finder.env
```

Fill `/etc/micro-niche-finder.env` with production secrets.

For Google Custom Search, set `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_CX` explicitly in the environment file.
For Naver Search, you can either set `NAVER_SEARCH_CLIENT_ID` / `NAVER_SEARCH_CLIENT_SECRET` or let it reuse the Naver DataLab app credentials.
For Naver Shopping Insight, set `NAVER_SHOPPING_CATEGORY_OPTIONS_JSON` to the shopping categories you want the LLM to map into. This source is most useful for ecommerce, seller, and product niches.

For KOSIS market sizing, set `KOSIS_API_KEY`, `KOSIS_TBL_ID`, `KOSIS_EMPLOYEE_ITM_ID`, and `KOSIS_INDUSTRY_OPTIONS_JSON`.
`KOSIS_INDUSTRY_OPTIONS_JSON` should be a JSON array like `[{"code":"P","label":"교육 서비스업","description":"학원, 교육 서비스"}]`.

## Database

```bash
cd /opt/micro-niche-finder
source .venv/bin/activate
alembic upgrade head
python scripts/bootstrap_collection_schedules.py
```

## systemd

```bash
sudo cp deploy/systemd/micro-niche-api.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-collector.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-collector.timer /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-google-collector.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-google-collector.timer /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-naver-search-collector.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-naver-search-collector.timer /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-naver-shopping-insight-collector.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-naver-shopping-insight-collector.timer /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-kosis-collector.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-kosis-collector.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now micro-niche-api.service
sudo systemctl enable --now micro-niche-collector.timer
sudo systemctl enable --now micro-niche-google-collector.timer
sudo systemctl enable --now micro-niche-naver-search-collector.timer
sudo systemctl enable --now micro-niche-naver-shopping-insight-collector.timer
sudo systemctl enable --now micro-niche-kosis-collector.timer
```

## What Runs

- `micro-niche-api.service`: keeps the FastAPI app running.
- `micro-niche-collector.timer`: wakes the collector every 15 minutes.
- `micro-niche-collector.service`: computes the current budget allowance and collects only the due schedules it can afford.
- `micro-niche-google-collector.timer`: wakes the Google collector every 30 minutes.
- `micro-niche-google-collector.service`: samples Google Custom Search queries for cross-source validation.
- `micro-niche-naver-search-collector.timer`: refreshes Naver Search evidence every 30 minutes.
- `micro-niche-naver-search-collector.service`: samples Naver web search evidence for demand/context validation.
- `micro-niche-naver-shopping-insight-collector.timer`: refreshes Shopping Insight evidence every 2 hours for commerce-relevant niches.
- `micro-niche-naver-shopping-insight-collector.service`: samples Naver shopping-click category trends as supplementary commerce evidence.
- `micro-niche-kosis-collector.timer`: refreshes KOSIS employee-count market-size references every 6 hours.
- `micro-niche-kosis-collector.service`: samples KOSIS employee-count data for mapped industries.

## Manual checks

```bash
sudo systemctl status micro-niche-api.service
sudo systemctl status micro-niche-collector.timer
sudo systemctl status micro-niche-google-collector.timer
sudo systemctl status micro-niche-naver-search-collector.timer
sudo systemctl status micro-niche-naver-shopping-insight-collector.timer
sudo systemctl status micro-niche-kosis-collector.timer
sudo journalctl -u micro-niche-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-google-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-naver-search-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-naver-shopping-insight-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-kosis-collector.service -n 100 --no-pager
source .venv/bin/activate
python -m apps.worker.run_collector --max-calls 5
python -m apps.worker.run_google_collector --max-calls 3
python -m apps.worker.run_naver_search_collector --max-calls 3
python -m apps.worker.run_naver_shopping_insight_collector
python -m apps.worker.run_kosis_collector --max-calls 3
```

## Budget model

- Daily limit defaults to `1000`.
- The allocator divides remaining calls by the number of remaining timer slots for the day.
- With a 15-minute timer, the collector tries to consume the daily budget smoothly instead of front-loading all calls.
- Google Custom Search has its own daily limit and is treated as a supplementary source, not the primary ranking source.
- Naver Search is a supplementary demand-evidence source for narrow keyword niches and does not replace trend collection.
- Naver Shopping Insight is only useful for commerce/product niches, so it is intentionally scheduled selectively instead of for every query group.
- KOSIS employee-count collection is a supplementary market-size reference and does not change niche scoring by itself.
