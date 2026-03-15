# JobHelp Version 1

A configurable job board scraper that searches for tech leadership roles posted in the last 24 hours and emails you a digest with clickable links to every posting.

---

## Supported Job Boards

| Board | Method | Auth Required |
|-------|--------|--------------|
| Indeed | RSS feed | None |
| LinkedIn | Public guest API | None |
| Dice | Internal search API | None |
| The Muse | Public API | None |
| RemoteOK | Public JSON API | None |
| Jobicy | Public API | None |
| ZipRecruiter | Web scraping | None |
| Glassdoor | Web scraping | None |
| SimplyHired | Web scraping | None |
| Monster | Web scraping | None |
| CareerBuilder | Web scraping | None |
| **Adzuna** | Official API | **Free key** (optional) |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

Edit `.env`:

```
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password — see below
```

> **Gmail App Password**: Your regular Gmail password will NOT work.
> You must create an App Password at:
> https://myaccount.google.com/apppasswords
> (requires 2-Step Verification to be enabled on your account)

### 3. (Optional) Enable Adzuna

Register for a free API key at https://developer.adzuna.com/, then add to `.env`:

```
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
```

Then in `config.yaml` set `job_boards.adzuna.enabled: true`.

---

## Usage

| Command | What it does |
|---------|-------------|
| `python main.py` | Run once immediately, then keep running on the configured schedule |
| `python main.py --now` | Scrape all boards and send the email right now, then exit |
| `python main.py --dry-run` | Scrape all boards and print results to terminal, no email sent |
| `python main.py --list-boards` | Print all supported boards and exit |
| `python main.py --config other.yaml` | Use a different config file |

---

## Configuration (`config.yaml`)

### Job Titles

Add or remove titles freely:

```yaml
job_titles:
  - "CTO"
  - "CIO"
  - "VP of Technology"
  - "Head of IT"
  - "Head of Infrastructure"
  - "SVP of Technology"
  - "EUC"
  - "Director of Technology"
```

### Enable / Disable Boards

```yaml
job_boards:
  indeed:
    enabled: true
  linkedin:
    enabled: false   # ← flip to false to skip
```

### Search Filters

```yaml
search:
  hours_ago: 24        # only jobs posted within this window
  location: ""         # blank = nationwide; e.g. "New York, NY"
  remote_ok: true
  results_per_board: 25
```

### Email Schedule

```yaml
email:
  recipient: "cmoskowitz@gmail.com"
  schedule: "daily"        # "daily", "hourly", or a custom "HH:MM"
  daily_time: "08:00"      # used when schedule = "daily"
  timezone: "America/New_York"
```

---

## Running as a Background Service

### Linux (systemd)

Create `/etc/systemd/system/jobhelp.service`:

```ini
[Unit]
Description=JobHelp Version 1
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/JobHelp
ExecStart=/usr/bin/python3 /path/to/JobHelp/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable jobhelp
sudo systemctl start jobhelp
```

### macOS (launchd) or cron

Simple cron alternative — run at 8 AM daily:

```cron
0 8 * * * cd /path/to/JobHelp && python3 main.py --now >> jobhelp.log 2>&1
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

---

## Adding a New Job Board

1. Open `scrapers.py`
2. Create a class that extends `BaseScraper`
3. Implement `fetch(self, job_title: str) -> List[Job]`
4. Register it in `SCRAPER_REGISTRY` at the bottom of the file
5. Add an entry to `config.yaml` under `job_boards`

---

## Notes on Anti-Bot Measures

LinkedIn, Glassdoor, ZipRecruiter, and other large boards actively detect and block automated scrapers. Results from these boards may vary. The scrapers use realistic browser headers and rate limiting, but you may see fewer results from these boards over time. The API-based boards (Indeed RSS, Dice, RemoteOK, Jobicy, The Muse, Adzuna) are the most reliable.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-03-15 | Initial release — 12 boards, HTML email digest, configurable schedule |
