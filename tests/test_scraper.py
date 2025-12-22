"""
Unit tests for the scraper module.
Uses a saved HTML fixture to avoid hitting the live website.
"""

import unittest
from pathlib import Path

from scraper import parse_listing
from store import generate_listing_id
from bs4 import BeautifulSoup


class TestScraper(unittest.TestCase):
    """Test scraper parsing logic."""
    
    def setUp(self):
        """Load HTML fixture."""
        fixture_path = Path(__file__).parent / "fixture.html"
        if not fixture_path.exists():
            # Create a minimal fixture if it doesn't exist
            self.html = """
            <html>
            <body>
                <h2>Homes for Sale</h2>
                <div class="listing">
                    <h3>4420 C Groombridge Way</h3>
                    <p>Status: DRAWING CLOSED</p>
                    <p>Price: $106,516</p>
                    <p>Location: Alexandria, VA 22309</p>
                    <p>Type: Condominium</p>
                    <p>Household: 1 to 4 people</p>
                    <p>2 Bedrooms / 1 Bathroom</p>
                    <a href="/housing/homeownership/listing/123">Full Listing</a>
                </div>
                <div class="listing">
                    <h3>123 Main Street</h3>
                    <p>Status: IMMEDIATELY AVAILABLE</p>
                    <p>Price: $150,000</p>
                    <p>Location: Fairfax, VA 22030</p>
                    <p>Type: Townhouse</p>
                    <p>Household: 2 to 5 people</p>
                    <p>3 Bedrooms / 2 Bathrooms</p>
                    <a href="/housing/homeownership/listing/456">View Listing</a>
                </div>
            </body>
            </html>
            """
        else:
            self.html = fixture_path.read_text(encoding="utf-8")
    
    def test_parse_listing(self):
        """Test parsing a single listing block."""
        soup = BeautifulSoup(self.html, "lxml")
        listings = soup.find_all("div", class_="listing")
        
        self.assertGreater(len(listings), 0, "Should find at least one listing")
        
        # Parse first listing
        base_url = "https://www.fairfaxcounty.gov/housing/homeownership/FirstTimeHomebuyers"
        listing = parse_listing(listings[0], base_url)
        
        self.assertIsNotNone(listing, "Should parse listing successfully")
        self.assertIn("title", listing)
        self.assertIn("status", listing)
        self.assertIn("price", listing)
        self.assertIn("location", listing)
        self.assertIn("url", listing)
        
        # Check specific fields
        self.assertIn("Groombridge", listing["title"])
        self.assertEqual("DRAWING CLOSED", listing["status"])
        self.assertIn("106,516", listing["price"])
        self.assertIn("Alexandria", listing["location"])
        self.assertIn("Condominium", listing["details_text"])
        self.assertIn("Full Listing", listing["url"] or "")
    
    def test_generate_listing_id(self):
        """Test listing ID generation."""
        listing1 = {
            "url": "https://example.com/listing/123",
            "title": "Test Listing",
            "price": "$100,000",
            "location": "City, ST 12345"
        }
        
        listing2 = {
            "url": "https://example.com/listing/123",
            "title": "Different Title",
            "price": "$200,000",
            "location": "Other City, ST 67890"
        }
        
        listing3 = {
            "url": "",
            "title": "Test Listing",
            "price": "$100,000",
            "location": "City, ST 12345"
        }
        
        # Same URL should generate same ID
        id1 = generate_listing_id(listing1)
        id2 = generate_listing_id(listing2)
        self.assertEqual(id1, id2, "Same URL should generate same ID")
        
        # Different listings without URL should generate different IDs
        id3 = generate_listing_id(listing3)
        self.assertNotEqual(id1, id3, "Different listings should generate different IDs")
        
        # Same content without URL should generate same ID
        listing4 = {
            "url": "",
            "title": "Test Listing",
            "price": "$100,000",
            "location": "City, ST 12345"
        }
        id4 = generate_listing_id(listing4)
        self.assertEqual(id3, id4, "Same content should generate same ID")


if __name__ == "__main__":
    unittest.main()

