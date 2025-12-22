# GitHub Actions Setup Guide

This guide walks you through setting up GitHub Actions to automatically run the Fairfax FTHB Notifier every 12 hours.

## Step-by-Step Instructions

### Step 1: Commit Your Code Locally

First, make sure all your code is committed:

```bash
git add .
git commit -m "Add GitHub Actions workflows for automation"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. **Repository name**: Choose a name (e.g., `fairfax-fthb-notifier`)
3. **Description**: Optional (e.g., "Automated notifier for Fairfax County First-Time Homebuyers listings")
4. **Visibility**: 
   - **Public** = Free GitHub Actions (recommended)
   - **Private** = Requires GitHub Pro/Team (paid)
5. **DO NOT** check "Initialize with README" (you already have one)
6. Click **"Create repository"**

### Step 3: Push Your Code to GitHub

Copy the commands GitHub shows you, or use these (replace `YOUR_USERNAME` and `YOUR_REPO_NAME`):

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 4: Add GitHub Secrets

GitHub Secrets store your sensitive information (email credentials) securely:

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **"New repository secret"** button
5. Add each secret one by one:

   **Required Secrets:**
   - Name: `SMTP_HOST` → Value: `smtp.gmail.com`
   - Name: `SMTP_PORT` → Value: `587`
   - Name: `SMTP_USER` → Value: `your-email@gmail.com`
   - Name: `SMTP_PASS` → Value: `your-app-password` (Gmail app password)
   - Name: `EMAIL_FROM` → Value: `your-email@gmail.com`
   - Name: `EMAIL_TO` → Value: `recipient@example.com`

   **Optional Secrets:**
   - Name: `EMAIL_SUBJECT_PREFIX` → Value: `Fairfax FTHB` (optional)
   - Name: `ALWAYS_EMAIL` → Value: `false` (optional)

6. Click **"Add secret"** after each one

**Important**: For Gmail, you need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Step 5: Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. You should see two workflows:
   - **Fairfax FTHB Notifier** (main workflow - runs every 12 hours)
   - **Refresh Database Artifact** (maintenance workflow - runs monthly)
3. If you see a message about enabling workflows, click **"I understand my workflows, enable them"**

### Step 6: Test the Workflow Manually

Before waiting for the scheduled run, test it manually:

1. Go to **Actions** tab
2. Click on **"Fairfax FTHB Notifier"** workflow
3. Click **"Run workflow"** dropdown button (top right)
4. Click **"Run workflow"** button
5. Watch the workflow run in real-time
6. Check the logs to see if it worked

**What to expect:**
- First run: Will create a new database (no previous artifact)
- Subsequent runs: Will download previous database and update it
- If there are new listings, an email will be sent
- The updated database will be uploaded as an artifact

### Step 7: Verify It's Working

1. **Check workflow runs**: Go to Actions tab → You should see workflow runs
2. **Check artifacts**: After a successful run, go to the workflow run → Scroll down → You should see "Artifacts" section with `listings-db`
3. **Check your email**: You should receive an email if there are new listings
4. **Check logs**: Click on a workflow run to see detailed logs

### Step 8: Monitor and Troubleshoot

**Workflow Schedule:**
- **Main workflow**: Runs every 12 hours (00:00 and 12:00 UTC)
- **Refresh workflow**: Runs monthly on the 1st at 2 AM UTC

**Common Issues:**

1. **Workflow not running**:
   - Check if Actions are enabled (Settings → Actions → General)
   - Verify the cron schedule is correct
   - Check if you're on a free plan (public repos get free Actions)

2. **"Missing required environment variables"**:
   - Double-check all secrets are added correctly
   - Secret names must match exactly (case-sensitive)

3. **Email not sending**:
   - Verify SMTP credentials are correct
   - Check workflow logs for specific error messages
   - Make sure you're using a Gmail App Password (not regular password)

4. **Database not persisting**:
   - Check that artifacts are being created (look in workflow run)
   - Verify the refresh workflow is enabled
   - Artifacts expire after 90 days, but refresh workflow extends them

## How It Works

1. **Every 12 hours**: Main workflow runs
   - Downloads previous `listings.db` artifact (if exists)
   - Runs the scraper
   - Sends email for new listings
   - Uploads updated database as artifact

2. **Monthly**: Refresh workflow runs
   - Downloads current artifact
   - Re-uploads it (resets 90-day expiration timer)
   - Ensures database never expires

## Viewing Your Database

You can download the database artifact to inspect it locally:

1. Go to Actions → Latest workflow run
2. Scroll to "Artifacts" section
3. Click `listings-db` → Download
4. Extract the zip file
5. Open `listings.db` with SQLite browser or command line:
   ```bash
   sqlite3 listings.db "SELECT * FROM listings;"
   ```

## Disabling/Modifying Workflows

**To disable workflows:**
- Go to Actions → Select workflow → Click "..." → "Disable workflow"

**To modify schedule:**
- Edit `.github/workflows/notifier.yml`
- Change the cron schedule: `cron: '0 */12 * * *'`
- Commit and push changes

**To run manually anytime:**
- Go to Actions → Workflow → "Run workflow" button

## Next Steps

Once set up:
- ✅ Workflows run automatically every 12 hours
- ✅ Database persists via artifacts
- ✅ Artifacts auto-refresh monthly
- ✅ You'll receive emails for new listings
- ✅ No computer needed - runs 24/7 in the cloud!

