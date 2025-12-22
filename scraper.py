"""
Scraper for Fairfax County First-Time Homebuyers listings.
Fetches and parses the listings page to extract home information.
"""

import logging
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Base URL for the Fairfax County FTHB page
BASE_URL = "https://www.fairfaxcounty.gov/housing/homeownership/FirstTimeHomebuyers"

# User-Agent to identify the scraper
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


def fetch_page(url: str, timeout: int = 30, max_retries: int = 3) -> str:
    """
    Fetch HTML content from a URL with retries and backoff.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        HTML content as string
        
    Raises:
        ScraperError: If all retries fail
    """
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Fetch attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise ScraperError(f"Failed to fetch {url} after {max_retries} attempts: {e}")


def extract_listing_text(element) -> str:
    """Extract and clean text from a BeautifulSoup element."""
    if element is None:
        return ""
    return element.get_text(strip=True, separator=" ")


def find_listing_url(element, base_url: str) -> Optional[str]:
    """
    Find the "Full Listing" URL in a listing element.
    Looks for links containing "Full Listing" or similar text.
    """
    if element is None:
        return None
    
    # Look for links with "Full Listing" text
    links = element.find_all("a", href=True)
    for link in links:
        link_text = link.get_text(strip=True).lower()
        if "full listing" in link_text or "view listing" in link_text or "listing" in link_text:
            href = link.get("href", "")
            if href:
                # Convert to absolute URL
                return urljoin(base_url, href)
    
    # Fallback: look for any link that might be the listing URL
    if links:
        href = links[0].get("href", "")
        if href and not href.startswith("#"):
            return urljoin(base_url, href)
    
    return None


def parse_listing(block, base_url: str) -> Optional[Dict[str, str]]:
    """
    Parse a single listing block into a dictionary.
    
    Args:
        block: BeautifulSoup element containing a listing
        base_url: Base URL for resolving relative links
        
    Returns:
        Dictionary with listing fields, or None if parsing fails
    """
    try:
        listing = {}
        
        # Extract title (usually in a heading or first strong/bold text)
        title = None
        for tag in ["h2", "h3", "h4", "strong", "b"]:
            title_elem = block.find(tag)
            if title_elem:
                title = extract_listing_text(title_elem)
                break
        
        # If no heading found, try first line of text
        if not title:
            first_text = block.get_text(strip=True).split("\n")[0]
            if first_text:
                title = first_text[:200]  # Limit length
        
        if not title:
            return None
        
        listing["title"] = title
        
        # Extract status (look for "DRAWING CLOSED", "IMMEDIATELY AVAILABLE", etc.)
        status = ""
        block_text = block.get_text().lower()
        if "drawing closed" in block_text:
            status = "DRAWING CLOSED"
        elif "immediately available" in block_text:
            status = "IMMEDIATELY AVAILABLE"
        elif "available" in block_text:
            status = "AVAILABLE"
        
        listing["status"] = status
        
        # Extract price (look for $ followed by numbers)
        price = ""
        price_match = re.search(r'\$[\d,]+', block_text)
        if price_match:
            price = price_match.group(0)
        listing["price"] = price
        
        # Extract location (look for city, state, zip patterns)
        location = ""
        location_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s+(\d{5})', block_text)
        if location_match:
            location = location_match.group(0)
        listing["location"] = location
        
        # Extract key details (property type, household size, beds/baths)
        details_lines = []
        
        # Property type
        if "condominium" in block_text.lower() or "condo" in block_text.lower():
            details_lines.append("Type: Condominium")
        elif "townhouse" in block_text.lower() or "town home" in block_text.lower():
            details_lines.append("Type: Townhouse")
        elif "single family" in block_text.lower():
            details_lines.append("Type: Single Family")
        
        # Household size
        household_match = re.search(r'(\d+)\s+to\s+(\d+)\s+people?', block_text, re.IGNORECASE)
        if household_match:
            details_lines.append(f"Household: {household_match.group(0)}")
        
        # Beds/Baths
        beds_match = re.search(r'(\d+)\s+bedroom', block_text, re.IGNORECASE)
        baths_match = re.search(r'(\d+)\s+bathroom', block_text, re.IGNORECASE)
        if beds_match or baths_match:
            beds = beds_match.group(0) if beds_match else "N/A"
            baths = baths_match.group(0) if baths_match else "N/A"
            details_lines.append(f"Beds/Baths: {beds} / {baths}")
        
        listing["details_text"] = "\n".join(details_lines)
        
        # Extract Full Listing URL
        url = find_listing_url(block, base_url)
        listing["url"] = url or ""
        
        return listing
        
    except Exception as e:
        logger.warning(f"Error parsing listing block: {e}")
        return None


def scrape_listings(url: str = BASE_URL) -> List[Dict[str, str]]:
    """
    Scrape listings from the Fairfax County FTHB page.
    
    Args:
        url: URL to scrape (defaults to BASE_URL)
        
    Returns:
        List of listing dictionaries
        
    Raises:
        ScraperError: If scraping fails
    """
    try:
        html = fetch_page(url)
        soup = BeautifulSoup(html, "lxml")
        
        # Find the "Homes for Sale" section
        # Look for headings containing "Homes for Sale" or similar
        homes_section = None
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            heading_text = heading.get_text(strip=True).lower()
            if "homes for sale" in heading_text or "available homes" in heading_text:
                # Find the parent container or next siblings
                homes_section = heading.find_parent(["div", "section", "article"]) or heading.parent
                break
        
        if not homes_section:
            # Fallback: search for common patterns
            homes_section = soup.find("div", class_=lambda x: x and ("listing" in x.lower() or "home" in x.lower()))
            if not homes_section:
                homes_section = soup.find("main") or soup.find("body")
        
        if not homes_section:
            raise ScraperError("Could not find 'Homes for Sale' section in HTML")
        
        listings = []
        
        # The actual structure: listings are h2 headings (title/status) followed by h3 (price)
        # Find the "Homes for Sale" h2 heading
        all_h2s = soup.find_all("h2")
        start_idx = -1
        for i, h2 in enumerate(all_h2s):
            if "homes for sale" in h2.get_text(strip=True).lower():
                start_idx = i
                break
        
        if start_idx == -1:
            raise ScraperError("Could not find 'Homes for Sale' heading")
        
        # Process each h2 that looks like a listing after "Homes for Sale"
        for i in range(start_idx + 1, len(all_h2s)):
            h2 = all_h2s[i]
            h2_text = h2.get_text(strip=True)
            
            # Stop if we hit another major section
            if any(stop_word in h2_text.lower() for stop_word in ["virtual assistant", "eligibility", "application", "step", "about"]):
                break
            
            # Skip if this h2 doesn't look like a listing
            if not ("$" in h2_text or "drawing" in h2_text.lower() or "available" in h2_text.lower() or 
                    any(word in h2_text.lower() for word in ["way", "street", "road", "drive", "court", "lane", "groombridge", "cavalier"])):
                continue
            
            # Collect all following siblings until next h2 to build the listing block
            # Use find_next_siblings to get everything until next h2
            siblings = h2.find_next_siblings(["h1", "h2", "h3", "h4", "p", "div", "a", "ul", "li"], limit=10)
            
            # Create a container div
            container = soup.new_tag("div")
            container.append(h2)  # Add the h2 itself
            
            # Add siblings until we hit another h2
            for sibling in siblings:
                if sibling.name == 'h2':
                    break
                container.append(sibling)
            
            listing = parse_listing(container, url)
            if listing and listing.get("title"):
                listings.append(listing)
        
        # Fallback: if we didn't find listings, try div-based approach
        if not listings:
            logger.warning("No listings found with h2/h3 parsing, trying div-based approach")
            potential_blocks = homes_section.find_all(["div", "article", "li"], recursive=True)
            
            for block in potential_blocks:
                block_text = block.get_text().lower()
                if len(block_text) < 50:
                    continue
                
                has_price = "$" in block_text
                has_address = any(word in block_text for word in ["way", "street", "road", "drive", "court", "lane", "alexandria", "fairfax", "springfield"])
                has_listing_link = "listing" in block_text or block.find("a", href=True)
                
                if has_price or has_address or has_listing_link:
                    listing = parse_listing(block, url)
                    if listing and listing.get("title"):
                        listings.append(listing)
        
        if not listings:
            raise ScraperError("No listings found on page. HTML structure may have changed.")
        
        logger.info(f"Successfully scraped {len(listings)} listings")
        return listings
        
    except ScraperError:
        raise
    except Exception as e:
        raise ScraperError(f"Unexpected error during scraping: {e}")

