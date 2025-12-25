"""
SQLite storage for tracking listings and preventing duplicates.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def generate_listing_id(listing: Dict[str, str]) -> str:
    """
    Generate a stable unique ID for a listing.
    
    Primary: Use the "Full Listing" URL if available.
    Fallback: Hash of (title + price + location).
    
    Args:
        listing: Listing dictionary
        
    Returns:
        Unique ID string
    """
    url = listing.get("url", "").strip()
    if url:
        return url
    
    # Fallback: hash of title + price + location
    title = listing.get("title", "").strip()
    price = listing.get("price", "").strip()
    location = listing.get("location", "").strip()
    
    combined = f"{title}|{price}|{location}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]


class ListingStore:
    """SQLite-based storage for listings with deduplication."""
    
    def __init__(self, db_path: str = "listings.db"):
        """
        Initialize the store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT,
                price TEXT,
                location TEXT,
                url TEXT,
                details_text TEXT,
                first_seen_at TIMESTAMP NOT NULL,
                last_seen_at TIMESTAMP NOT NULL,
                emailed_at TIMESTAMP
            )
        """)
        
        # Create index on emailed_at for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emailed_at 
            ON listings(emailed_at)
        """)
        
        conn.commit()
        conn.close()
        logger.debug(f"Initialized database at {self.db_path}")
    
    def upsert_listing(self, listing: Dict[str, str]) -> str:
        """
        Insert or update a listing.
        
        Args:
            listing: Listing dictionary
            
        Returns:
            The listing ID
        """
        listing_id = generate_listing_id(listing)
        now = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if listing exists
        cursor.execute("SELECT id FROM listings WHERE id = ?", (listing_id,))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update existing listing (but preserve emailed_at if it exists)
            cursor.execute("""
                UPDATE listings
                SET title = ?,
                    status = ?,
                    price = ?,
                    location = ?,
                    url = ?,
                    details_text = ?,
                    last_seen_at = ?
                WHERE id = ?
            """, (
                listing.get("title", ""),
                listing.get("status", ""),
                listing.get("price", ""),
                listing.get("location", ""),
                listing.get("url", ""),
                listing.get("details_text", ""),
                now,
                listing_id
            ))
            # Note: emailed_at is NOT updated here - it's preserved if it exists
        else:
            # Insert new listing
            cursor.execute("""
                INSERT INTO listings (
                    id, title, status, price, location, url, details_text,
                    first_seen_at, last_seen_at, emailed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """, (
                listing_id,
                listing.get("title", ""),
                listing.get("status", ""),
                listing.get("price", ""),
                listing.get("location", ""),
                listing.get("url", ""),
                listing.get("details_text", ""),
                now,
                now
            ))
        
        conn.commit()
        conn.close()
        
        return listing_id
    
    def get_unemailed_listings(self, exclude_closed: bool = False) -> List[Dict[str, str]]:
        """
        Get all listings that have never been emailed.
        
        Args:
            exclude_closed: If True, exclude listings with "DRAWING CLOSED" status
            
        Returns:
            List of listing dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if exclude_closed:
            cursor.execute("""
                SELECT * FROM listings
                WHERE emailed_at IS NULL
                AND (status IS NULL OR status != 'DRAWING CLOSED')
                ORDER BY first_seen_at ASC
            """)
        else:
            cursor.execute("""
                SELECT * FROM listings
                WHERE emailed_at IS NULL
                ORDER BY first_seen_at ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        listings = []
        for row in rows:
            listings.append({
                "id": row["id"],
                "title": row["title"],
                "status": row["status"] or "",
                "price": row["price"] or "",
                "location": row["location"] or "",
                "url": row["url"] or "",
                "details_text": row["details_text"] or "",
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "emailed_at": row["emailed_at"]
            })
        
        return listings
    
    def mark_as_emailed(self, listing_ids: List[str]):
        """
        Mark listings as emailed.
        
        Args:
            listing_ids: List of listing IDs to mark
        """
        if not listing_ids:
            logger.warning("mark_as_emailed called with empty list")
            return
        
        now = datetime.utcnow()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First, verify these IDs exist
        placeholders = ",".join("?" * len(listing_ids))
        cursor.execute(f"""
            SELECT id FROM listings WHERE id IN ({placeholders})
        """, listing_ids)
        existing_ids = [row[0] for row in cursor.fetchall()]
        
        if len(existing_ids) != len(listing_ids):
            missing = set(listing_ids) - set(existing_ids)
            logger.warning(f"Some listing IDs not found in database: {missing}")
        
        # Update the listings
        cursor.execute(f"""
            UPDATE listings
            SET emailed_at = ?
            WHERE id IN ({placeholders})
        """, (now, *listing_ids))
        
        rows_updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Marked {rows_updated} listings as emailed (requested {len(listing_ids)})")
        
        # Verify the update
        if rows_updated != len(listing_ids):
            logger.warning(f"Expected to update {len(listing_ids)} listings, but only {rows_updated} were updated")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about stored listings.
        
        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM listings")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM listings WHERE emailed_at IS NOT NULL")
        emailed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM listings WHERE emailed_at IS NULL")
        unemailed = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "emailed": emailed,
            "unemailed": unemailed
        }

