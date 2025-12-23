#!/usr/bin/env python3
"""
Fairfax FTHB Listings Notifier - Main entry point.

Runs the scraper, stores listings, and sends emails for new listings.
"""

import argparse
import logging
import sys
from typing import List, Dict

from config import Config
from emailer import EmailError, send_email, format_email_body
from scraper import ScraperError, scrape_listings
from store import ListingStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_once(config: Config, exclude_closed: bool = False, dry_run: bool = False) -> Dict[str, int]:
    """
    Run a single scrape cycle.
    
    Args:
        config: Configuration instance
        exclude_closed: Whether to exclude "DRAWING CLOSED" listings
        dry_run: If True, don't send email or mark as emailed
        
    Returns:
        Dictionary with metrics: scraped_total, new_unemailed, emailed_count
    """
    metrics = {
        "scraped_total": 0,
        "new_unemailed": 0,
        "emailed_count": 0
    }
    
    store = ListingStore(db_path=config.DB_PATH)
    
    try:
        # Scrape listings
        logger.info("Starting scrape...")
        listings = scrape_listings()
        metrics["scraped_total"] = len(listings)
        logger.info(f"Scraped {len(listings)} listings")
        
        # Upsert all listings
        for listing in listings:
            store.upsert_listing(listing)
        
        # Get unemailed listings
        unemailed = store.get_unemailed_listings(exclude_closed=exclude_closed)
        metrics["new_unemailed"] = len(unemailed)
        logger.info(f"Found {len(unemailed)} new unemailed listings")
        
        # Always send email (even if no new listings)
        if dry_run:
            logger.info("DRY RUN - Would send email:")
            print("\n" + "=" * 80)
            if unemailed:
                print(format_email_body(unemailed))
            else:
                print("There are no new listings today.")
            print("=" * 80 + "\n")
            metrics["emailed_count"] = len(unemailed) if unemailed else 0
        else:
            # Send email (will include "no new listings" message if empty)
            try:
                send_email(config, unemailed)
                # Mark as emailed only after successful send and only if there are listings
                if unemailed:
                    listing_ids = [listing["id"] for listing in unemailed]
                    store.mark_as_emailed(listing_ids)
                    metrics["emailed_count"] = len(unemailed)
                    logger.info(f"Successfully emailed {len(unemailed)} listings")
                else:
                    logger.info("Successfully sent email: No new listings today")
                    metrics["emailed_count"] = 0
            except EmailError as e:
                logger.error(f"Failed to send email: {e}")
                if unemailed:
                    logger.error("Listings were NOT marked as emailed - will retry on next run")
                raise
        
        # Log stats
        stats = store.get_stats()
        logger.info(f"Database stats: {stats['total']} total, {stats['emailed']} emailed, {stats['unemailed']} unemailed")
        
        return metrics
        
    except ScraperError as e:
        logger.error(f"Scraper error: {e}")
        logger.error("Aborting run - no email sent, no listings marked as emailed")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        logger.error("Aborting run - no email sent, no listings marked as emailed")
        raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fairfax FTHB Listings Notifier - Scrape and email new listings"
    )
    parser.add_argument(
        "--exclude-closed",
        action="store_true",
        help="Exclude listings marked as 'DRAWING CLOSED'"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be emailed without sending"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scrape cycle and exit (for cron/scheduling)"
    )
    
    args = parser.parse_args()
    
    try:
        config = Config.load()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    if args.once:
        # Run once and exit
        try:
            metrics = run_once(config, exclude_closed=args.exclude_closed, dry_run=args.dry_run)
            logger.info(f"Run complete: scraped={metrics['scraped_total']}, "
                       f"new={metrics['new_unemailed']}, emailed={metrics['emailed_count']}")
            sys.exit(0)
        except (ScraperError, EmailError) as e:
            logger.error(f"Run failed: {e}")
            sys.exit(1)
    else:
        # Continuous mode (12-hour loop)
        import time
        logger.info("Starting continuous mode (12-hour polling)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                try:
                    metrics = run_once(config, exclude_closed=args.exclude_closed, dry_run=args.dry_run)
                    logger.info(f"Cycle complete: scraped={metrics['scraped_total']}, "
                               f"new={metrics['new_unemailed']}, emailed={metrics['emailed_count']}")
                except (ScraperError, EmailError) as e:
                    logger.error(f"Cycle failed: {e}")
                    logger.error("Will retry in 12 hours")
                
                # Wait 12 hours (43200 seconds)
                logger.info("Sleeping for 12 hours...")
                time.sleep(43200)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            sys.exit(0)


if __name__ == "__main__":
    main()

