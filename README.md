# Fairfax FTHB Listings Notifier

A production-ready Python application that automatically scrapes home listings from Fairfax County's First-Time Homebuyers Program page and emails you new listings every 12 hours. Never receives duplicate emails - each listing is sent exactly once.

## Features

- **Automated Scraping**: Fetches listings from the Fairfax County FTHB page every 12 hours
- **Deduplication**: Uses SQLite to track all listings and ensures each listing is emailed exactly once
- **Email Notifications**: Sends plain text emails with new listings via SMTP (Gmail supported)
- **Robust Error Handling**: Gracefully handles network errors, HTML changes, and email failures
- **Flexible Filtering**: Optional flag to exclude "DRAWING CLOSED" listings
- **Dry Run Mode**: Test what would be emailed without actually sending

## Requirements

- Python 3.11 or higher
- Internet connection
- SMTP email account (Gmail app password recommended)

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   
   Create a `.env` file or export these variables in your shell:
   ```bash
   # SMTP Settings (required)
   export SMTP_HOST="smtp.gmail.com"
   export SMTP_PORT="587"
   export SMTP_USER="moiassrm@gmail.com"
   export SMTP_PASS="obzj fvvc gymf ljqz"
   
   # Email Settings (required)
   export EMAIL_FROM="moiassrm@gmail.com"
   export EMAIL_TO="moiassrdinho80@gmail.com"
   
   # Optional Settings
   export EMAIL_SUBJECT_PREFIX="Fairfax FTHB"  # Default: "Fairfax FTHB"
   export ALWAYS_EMAIL="false"  # Send email even if no new listings (default: false)
   export DB_PATH="listings.db"  # SQLite database path (default: listings.db)
   ```

   **For Gmail users**: You'll need to create an [App Password](https://support.google.com/accounts/answer/185833) instead of using your regular password.

## Usage

### Run Once (for cron/scheduling)

```bash
python main.py --once
```

This runs a single scrape cycle and exits. Perfect for cron jobs.

### Continuous Mode (12-hour loop)

```bash
python main.py
```

Runs continuously, scraping every 12 hours. Press Ctrl+C to stop.

### Command-Line Options

- `--exclude-closed`: Exclude listings marked as "DRAWING CLOSED"
- `--dry-run`: Print what would be emailed without actually sending
- `--once`: Run a single scrape cycle and exit (for cron)

**Examples**:
```bash
# Test run without sending email
python main.py --once --dry-run

# Run once, excluding closed listings
python main.py --once --exclude-closed

# Continuous mode with closed listings excluded
python main.py --exclude-closed
```

## Scheduling

### Option A: Cron (Recommended)

Cron is the simplest and most reliable way to schedule the script.

**Linux/macOS**:

1. Open your crontab:
   ```bash
   crontab -e
   ```

2. Add a line to run the script every 12 hours (at midnight and noon):
   ```cron
   0 0,12 * * * cd /path/to/Home_Notification && /usr/bin/python3 main.py --once >> /path/to/Home_Notification/cron.log 2>&1
   ```

   Or if you prefer different times (e.g., 6 AM and 6 PM):
   ```cron
   0 6,18 * * * cd /path/to/Home_Notification && /usr/bin/python3 main.py --once >> /path/to/Home_Notification/cron.log 2>&1
   ```

3. Make sure to:
   - Replace `/path/to/Home_Notification` with your actual project path
   - Replace `/usr/bin/python3` with your Python 3.11+ path (find it with `which python3`)
   - Set up your environment variables in the crontab or use a `.env` file

**Setting environment variables in cron**:

Option 1: Load from `.env` file (requires `python-dotenv`):
```cron
0 0,12 * * * cd /path/to/Home_Notification && source .env && /usr/bin/python3 main.py --once >> cron.log 2>&1
```

Option 2: Export in crontab:
```cron
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
0 0,12 * * * cd /path/to/Home_Notification && /usr/bin/python3 main.py --once >> cron.log 2>&1
```

**Windows Task Scheduler**:

⚠️ **Note**: Task Scheduler requires your computer to be **on and awake**. If your computer is off or sleeping, scheduled tasks won't run.

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily, repeat every 12 hours
4. Action: Start a program
   - Program: `C:\Python311\python.exe` (or your Python path)
   - Arguments: `main.py --once`
   - Start in: `C:\Users\moias\OneDrive\Documents\Home_Notification`
5. Set environment variables in the task's environment settings

### Option B: GitHub Actions (Runs 24/7, No Computer Needed)

GitHub Actions can run your script automatically every 12 hours, even when your computer is off. The database is stored as a GitHub artifact and automatically refreshed monthly to prevent expiration.

**Setup Instructions:**

1. **Push your code to GitHub** (see GitHub setup steps below)
2. **Add secrets** in your GitHub repository:
   - Go to your repo → Settings → Secrets and variables → Actions
   - Click "New repository secret" and add:
     - `SMTP_HOST` (e.g., `smtp.gmail.com`)
     - `SMTP_PORT` (e.g., `587`)
     - `SMTP_USER` (your email)
     - `SMTP_PASS` (your app password)
     - `EMAIL_FROM` (your email)
     - `EMAIL_TO` (recipient email)
     - `EMAIL_SUBJECT_PREFIX` (optional, default: `Fairfax FTHB`)
     - `ALWAYS_EMAIL` (optional, default: `false`)
3. **Enable workflows**: The workflows are already configured in `.github/workflows/`
4. **Test manually**: Go to Actions tab → "Fairfax FTHB Notifier" → "Run workflow"

**How it works:**
- Main workflow runs every 12 hours (00:00 and 12:00 UTC)
- Downloads previous `listings.db` artifact before running
- Uploads updated database after running
- Separate workflow refreshes artifacts monthly to prevent expiration

**Note**: Free GitHub Actions are available for public repositories. Private repos require GitHub Pro/Team.

### Option C: Docker

See the Docker section below for containerized deployment.

## Docker Deployment

### Building the Image

```bash
docker build -t fairfax-fthb-notifier .
```

### Running with Docker

**Option 1: External Scheduling (Recommended)**

Run the container once per 12 hours using cron or a scheduler:

```bash
# Run once
docker run --rm --env-file .env fairfax-fthb-notifier python main.py --once
```

Schedule this command with cron or your container orchestrator.

**Option 2: Internal Loop**

The container can run continuously with a 12-hour internal loop:

```bash
docker run -d --name fairfax-notifier --env-file .env --restart unless-stopped fairfax-fthb-notifier
```

**Note**: The internal loop approach is acceptable but cron is preferred for better reliability and resource management.

### Docker Compose Example

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  notifier:
    build: .
    env_file: .env
    volumes:
      - ./listings.db:/app/listings.db
    restart: unless-stopped
    command: python main.py
```

Run with:
```bash
docker-compose up -d
```

## Email Format

Emails are sent in plain text with a numbered list format:

```
1) 4420 C Groombridge Way (DRAWING CLOSED)
   Price: $106,516
   Location: Alexandria, VA 22309
   Type: Condominium
   Household: 1 to 4 people
   Beds/Baths: 2 Bedrooms / 1 Bathroom
   Link: https://www.fairfaxcounty.gov/housing/homeownership/listing/4420-groombridge

2) 7890 Springfield Drive (IMMEDIATELY AVAILABLE)
   Price: $125,000
   Location: Springfield, VA 22150
   Type: Townhouse
   Household: 2 to 5 people
   Beds/Baths: 3 Bedrooms / 2 Bathrooms
   Link: https://www.fairfaxcounty.gov/housing/homeownership/listing/7890-springfield
```

## How It Works

1. **Scraping**: Fetches the Fairfax County FTHB page HTML using `requests` with retries and timeouts
2. **Parsing**: Extracts listings from the "Homes for Sale" section using BeautifulSoup
3. **Deduplication**: Each listing gets a unique ID (based on URL or hash of title+price+location)
4. **Storage**: All listings are stored in SQLite with timestamps (`first_seen_at`, `last_seen_at`, `emailed_at`)
5. **Emailing**: Only listings where `emailed_at` is NULL are included in emails
6. **Marking**: After successful email send, `emailed_at` is set to prevent duplicates

## Database

The SQLite database (`listings.db` by default) stores:

- `id`: Unique identifier (URL or hash)
- `title`, `status`, `price`, `location`, `url`, `details_text`: Listing fields
- `first_seen_at`: When the listing was first discovered
- `last_seen_at`: When the listing was last seen (updated on each scrape)
- `emailed_at`: When the listing was emailed (NULL if never emailed)

You can inspect the database:
```bash
sqlite3 listings.db "SELECT * FROM listings;"
```

## Testing

Run the unit tests (uses a saved HTML fixture, doesn't hit the live site):

```bash
python -m pytest tests/
```

Or with unittest:
```bash
python -m unittest tests.test_scraper
```

## Logging

The application logs to stdout with structured logging:

- `INFO`: Normal operations (scraping, emailing, stats)
- `WARNING`: Retries, parsing issues
- `ERROR`: Failures that prevent email sending

When using cron, redirect logs to a file:
```cron
0 0,12 * * * cd /path/to/Home_Notification && python main.py --once >> cron.log 2>&1
```

## Troubleshooting

**"Missing required environment variables"**:
- Make sure all required environment variables are set (SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO)

**"Failed to fetch"**:
- Check your internet connection
- The website may be temporarily down
- Check if the URL has changed

**"No listings found"**:
- The HTML structure may have changed - check the website manually
- Run with `--dry-run` to see what's being parsed

**Email not sending**:
- Verify SMTP credentials (for Gmail, use an App Password)
- Check firewall/network settings
- Review logs for specific error messages

**Duplicate emails**:
- This shouldn't happen - check the database: `sqlite3 listings.db "SELECT id, title, emailed_at FROM listings;"`
- If you see issues, you can reset: `rm listings.db` (but you'll get all listings again)

## Project Structure

```
Home_Notification/
├── main.py              # CLI entry point
├── scraper.py           # Web scraping logic
├── store.py             # SQLite persistence
├── emailer.py           # SMTP email sending
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── Dockerfile           # Docker container definition
├── listings.db          # SQLite database (created on first run)
└── tests/
    ├── __init__.py
    ├── test_scraper.py  # Unit tests
    └── fixture.html     # HTML fixture for tests
```

## License

This project is provided as-is for personal use.

## Support

If the HTML structure of the Fairfax County page changes, the scraper may need updates. Check the logs for parsing errors and adjust `scraper.py` as needed.

