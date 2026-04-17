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

For Brave Search, set `BRAVE_SEARCH_API_KEY` explicitly in the environment file.
For Naver Search, you can either set `NAVER_SEARCH_CLIENT_ID` / `NAVER_SEARCH_CLIENT_SECRET` or let it reuse the Naver DataLab app credentials.
For Naver Shopping Insight, set `NAVER_SHOPPING_CATEGORY_OPTIONS_JSON` to the shopping categories you want the LLM to map into. This source is most useful for ecommerce, seller, and product niches.

For KOSIS market sizing, either:

- keep using the legacy single-profile fields `KOSIS_TBL_ID`, `KOSIS_EMPLOYEE_ITM_ID`, and `KOSIS_INDUSTRY_OPTIONS_JSON`, or
- prefer the newer `KOSIS_PROFILE_OPTIONS_JSON` plus `KOSIS_INDUSTRY_OPTIONS_JSON`

`KOSIS_INDUSTRY_OPTIONS_JSON` can still be a JSON array like `[{"code":"P","label":"교육 서비스업","description":"학원, 교육 서비스"}]`, but it can now also be a mapping object like `{"classification":"KSIC10","level":"중분류","mapping":{"스마트스토어":"G47912"}}`.
The recommended profile-based structure for KOSIS is documented in `README.md` under the KOSIS mapping section and expands the old employee-count model into structure, revenue, growth, demand, and regional profiles.
For Telegram or Gmail delivery, set the relevant fields if you want bot or email notifications. Required Telegram fields are `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Required Gmail fields are `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD`, `GMAIL_FROM_EMAIL`, and `GMAIL_TO_EMAILS`. For Gmail, use an app password rather than your normal account password.

Auto suspend can be paused from the GUI session by creating the session marker file. The watchdog checks both a session marker and a global marker:

```bash
python -m apps.worker.auto_suspend_control status
python -m apps.worker.auto_suspend_control disable
python -m apps.worker.auto_suspend_control enable
python -m apps.worker.auto_suspend_control toggle
```

Use `--scope global` if you want to pause suspend for everyone on the machine.

Optional desktop launchers are available under `deploy/desktop/` if you want one-click GUI toggles.

You can install them into the current user's menu with:

```bash
./scripts/install_auto_suspend_launchers.sh
```

To install them for `k` explicitly from a root shell:

```bash
./scripts/install_auto_suspend_launchers.sh --home /home/k
```

If you prefer to do it manually:

```bash
mkdir -p ~/.local/share/applications
cp deploy/desktop/micro-niche-finder-toggle-auto-suspend.desktop ~/.local/share/applications/
cp deploy/desktop/micro-niche-finder-disable-auto-suspend.desktop ~/.local/share/applications/
cp deploy/desktop/micro-niche-finder-enable-auto-suspend.desktop ~/.local/share/applications/
```

## Database

```bash
cd /opt/micro-niche-finder
source .venv/bin/activate
alembic upgrade head
python scripts/migrate_sqlite_to_postgres.py
python scripts/bootstrap_collection_schedules.py
```

If you are migrating an existing SQLite checkout, run the migration command before switching any long-running services over to PostgreSQL. The script copies the current `micro_niche_finder.db` snapshot into the target `DATABASE_URL`, resets PostgreSQL sequences, and preserves the current Alembic revision marker.

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
sudo cp deploy/systemd/micro-niche-seedless-v2.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-seedless-v2.timer /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-auto-seeds.service /etc/systemd/system/
sudo cp deploy/systemd/micro-niche-auto-seeds.timer /etc/systemd/system/
sudo cp deploy/systemd/repro-suspend-after-periodic.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now micro-niche-api.service
sudo systemctl enable --now micro-niche-collector.timer
sudo systemctl enable --now micro-niche-google-collector.timer
sudo systemctl enable --now micro-niche-naver-search-collector.timer
sudo systemctl enable --now micro-niche-naver-shopping-insight-collector.timer
sudo systemctl enable --now micro-niche-kosis-collector.timer
sudo systemctl enable --now micro-niche-seedless-v2.timer
sudo systemctl enable --now micro-niche-auto-seeds.timer
sudo systemctl disable --now micro-niche-daily-report.timer
```

## What Runs

- `micro-niche-api.service`: keeps the FastAPI app running.
- `micro-niche-collector.timer`: wakes the collector once per day.
- `micro-niche-collector.service`: computes the current budget allowance and collects only the due schedules it can afford.
- `micro-niche-google-collector.timer`: wakes the Google collector once per day.
- `micro-niche-google-collector.service`: samples Brave Search queries for cross-source validation.
- `micro-niche-naver-search-collector.timer`: refreshes Naver Search evidence once per day.
- `micro-niche-naver-search-collector.service`: samples Naver web search evidence for demand/context validation.
- `micro-niche-naver-shopping-insight-collector.timer`: refreshes Shopping Insight evidence once per day for commerce-relevant niches.
- `micro-niche-naver-shopping-insight-collector.service`: samples Naver shopping-click category trends as supplementary commerce evidence.
- `micro-niche-kosis-collector.timer`: refreshes KOSIS employee-count market-size references once per day.
- `micro-niche-kosis-collector.service`: samples KOSIS employee-count data for mapped industries.
- `micro-niche-seedless-v2.timer`: runs seedless discovery once per day.
- `micro-niche-seedless-v2.service`: performs the search-based discovery batch once per day.
- `micro-niche-auto-seeds.timer`: runs seed discovery and report generation once per day.
- `micro-niche-auto-seeds.service`: generates new seed categories, runs the pipeline, sends a Telegram summary, and writes a markdown copy under `llm-wiki/raw` inside the repository checkout.
- `micro-niche-daily-report.timer`: should stay disabled to avoid duplicate daily reports.
- `repro-suspend-after-periodic.service`: retries suspend after a periodic job finishes until the system actually becomes idle enough to suspend.

## Manual checks

```bash
sudo systemctl status micro-niche-api.service
sudo systemctl status micro-niche-collector.timer
sudo systemctl status micro-niche-google-collector.timer
sudo systemctl status micro-niche-naver-search-collector.timer
sudo systemctl status micro-niche-naver-shopping-insight-collector.timer
sudo systemctl status micro-niche-kosis-collector.timer
sudo systemctl status micro-niche-seedless-v2.timer
sudo systemctl status micro-niche-auto-seeds.timer
sudo journalctl -u micro-niche-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-google-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-naver-search-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-naver-shopping-insight-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-kosis-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-auto-seeds.service -n 100 --no-pager
source .venv/bin/activate
python -m apps.worker.run_collector --max-calls 5
python -m apps.worker.run_google_collector --max-calls 3
python -m apps.worker.run_naver_search_collector --max-calls 3
python -m apps.worker.run_naver_shopping_insight_collector
python -m apps.worker.run_kosis_collector --max-calls 3
python -m apps.worker.bootstrap_auto_seeds --seed-count 1 --candidate-count 1 --top-k 1 --evidence-mode minimal --log-detail summary --send-telegram --raw-output-dir llm-wiki/raw
python -m apps.worker.run_seedless_v2
```

## Budget model

- Daily limit defaults to `1000`.
- The allocator divides remaining calls by the number of remaining timer slots for the day.
- With a 30-minute timer, the collector still spreads the daily budget, but the run frequency is lower and the DB contention risk is smaller.
- Brave Search has its own monthly hard cap and is treated as a supplementary source, not the primary ranking source.
- Naver Search is a supplementary demand-evidence source for narrow keyword niches and does not replace trend collection.
- Naver Shopping Insight is only useful for commerce/product niches, so it is intentionally scheduled selectively instead of for every query group.
- KOSIS employee-count collection is a supplementary market-size reference and does not change niche scoring by itself.
