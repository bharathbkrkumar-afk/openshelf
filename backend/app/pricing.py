import os
import urllib.parse
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import httpx
import asyncio
from bs4 import BeautifulSoup

class PriceOffer(BaseModel):
    retailer: str
    title: str
    author: Optional[str]
    edition: Optional[str]
    isbn: Optional[str]
    format: str
    price_inr: float
    discount_percentage: Optional[float]
    availability: str
    shipping_cost_inr: Optional[float]
    product_url: str
    last_checked: str
    is_approximate_match: bool

class SearchLink(BaseModel):
    retailer: str
    url: str

class PricingResult(BaseModel):
    query: str
    offers: List[PriceOffer]
    search_links: List[SearchLink]
    errors: List[str]

RETAILERS = [
    "Amazon India",
    "Flipkart",
    "Meesho",
    "BooksWagon",
    "Crossword",
    "SapnaOnline",
    "Bookscape",
    "Pustakkosh"
]

def generate_search_link(retailer: str, query: str) -> str:
    encoded_query = urllib.parse.quote(query)
    match retailer:
        case "Amazon India":
            return f"https://www.amazon.in/s?k={encoded_query}&i=stripbooks"
        case "Flipkart":
            return f"https://www.flipkart.com/search?q={encoded_query}"
        case "Meesho":
            return f"https://www.meesho.com/search?q={encoded_query}"
        case "BooksWagon":
            return f"https://www.bookswagon.com/search-books/{encoded_query}"
        case "Crossword":
            return f"https://www.crossword.in/search?q={encoded_query}"
        case "SapnaOnline":
            return f"https://www.sapnaonline.com/search?q={encoded_query}"
        case "Bookscape":
            return f"https://bookscape.com/search?q={encoded_query}"
        case "Pustakkosh":
            return f"https://pustakkosh.com/search?q={encoded_query}"
        case _:
            return ""

def clean_price(text: str) -> float:
    try:
        clean_text = "".join(c for c in text if c.isdigit() or c == '.')
        return float(clean_text) if clean_text else 0.0
    except ValueError:
        return 0.0

async def fetch_bookswagon(query: str) -> Optional[PriceOffer]:
    url = f"https://www.bookswagon.com/search-books/{urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.list-view-books, .col-sm-12 .card')
                if items:
                    item = items[0]
                    title_elem = item.select_one('.title, .booktitle')
                    price_elem = item.select_one('.price, .sell')
                    if title_elem and price_elem:
                        price_inr = clean_price(price_elem.text)
                        if price_inr > 0:
                            return PriceOffer(
                                retailer="BooksWagon",
                                title=title_elem.text.strip()[:100],
                                format="Paperback",
                                price_inr=price_inr,
                                availability="Available",
                                product_url=url,
                                last_checked=datetime.now(timezone.utc).isoformat(),
                                is_approximate_match=True
                            )
        except Exception:
            pass
    return None

async def fetch_crossword(query: str) -> Optional[PriceOffer]:
    url = f"https://www.crossword.in/search?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.product-item')
                if items:
                    item = items[0]
                    title_elem = item.select_one('.product-item__title')
                    price_elem = item.select_one('.price-item')
                    if title_elem and price_elem:
                        price_inr = clean_price(price_elem.text)
                        if price_inr > 0:
                            return PriceOffer(
                                retailer="Crossword",
                                title=title_elem.text.strip()[:100],
                                format="Paperback",
                                price_inr=price_inr,
                                availability="Available",
                                product_url=url,
                                last_checked=datetime.now(timezone.utc).isoformat(),
                                is_approximate_match=True
                            )
        except Exception:
            pass
    return None

async def fetch_sapnaonline(query: str) -> Optional[PriceOffer]:
    url = f"https://www.sapnaonline.com/search?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.product-card, .search-product')
                if items:
                    item = items[0]
                    title_elem = item.select_one('.product-name, h3, h2')
                    price_elem = item.select_one('.price, .actual-price')
                    if title_elem and price_elem:
                        price_inr = clean_price(price_elem.text)
                        if price_inr > 0:
                            return PriceOffer(
                                retailer="SapnaOnline",
                                title=title_elem.text.strip()[:100],
                                format="Paperback",
                                price_inr=price_inr,
                                availability="Available",
                                product_url=url,
                                last_checked=datetime.now(timezone.utc).isoformat(),
                                is_approximate_match=True
                            )
        except Exception:
            pass
    return None

async def get_prices(query: str) -> PricingResult:
    offers = []
    search_links = []
    errors = []

    amazon_key = os.getenv("AMAZON_PAAPI_KEY")
    flipkart_key = os.getenv("FLIPKART_AFFILIATE_ID")
    
    tasks = [
        fetch_bookswagon(query),
        fetch_crossword(query),
        fetch_sapnaonline(query)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    scraped_retailers = []
    for res in results:
        if isinstance(res, PriceOffer):
            offers.append(res)
            scraped_retailers.append(res.retailer)

    for retailer in RETAILERS:
        if retailer in scraped_retailers:
            continue
            
        url = generate_search_link(retailer, query)
        if url:
            search_links.append(SearchLink(retailer=retailer, url=url))

    return PricingResult(
        query=query,
        offers=sorted(offers, key=lambda x: x.price_inr),
        search_links=search_links,
        errors=errors
    )
