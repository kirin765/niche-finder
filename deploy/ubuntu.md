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
sudo systemctl daemon-reload
sudo systemctl enable --now micro-niche-api.service
sudo systemctl enable --now micro-niche-collector.timer
sudo systemctl enable --now micro-niche-google-collector.timer
```

## What Runs

- `micro-niche-api.service`: keeps the FastAPI app running.
- `micro-niche-collector.timer`: wakes the collector every 15 minutes.
- `micro-niche-collector.service`: computes the current budget allowance and collects only the due schedules it can afford.
- `micro-niche-google-collector.timer`: wakes the Google collector every 30 minutes.
- `micro-niche-google-collector.service`: samples Google Custom Search queries for cross-source validation.

## Manual checks

```bash
sudo systemctl status micro-niche-api.service
sudo systemctl status micro-niche-collector.timer
sudo systemctl status micro-niche-google-collector.timer
sudo journalctl -u micro-niche-collector.service -n 100 --no-pager
sudo journalctl -u micro-niche-google-collector.service -n 100 --no-pager
source .venv/bin/activate
python -m apps.worker.run_collector --max-calls 5
python -m apps.worker.run_google_collector --max-calls 3
```

## Budget model

- Daily limit defaults to `1000`.
- The allocator divides remaining calls by the number of remaining timer slots for the day.
- With a 15-minute timer, the collector tries to consume the daily budget smoothly instead of front-loading all calls.
- Google Custom Search has its own daily limit and is treated as a supplementary source, not the primary ranking source.
