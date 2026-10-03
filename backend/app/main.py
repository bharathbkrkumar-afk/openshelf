from __future__ import annotations

import asyncio
from typing import Any
import os
import urllib.parse

from dotenv import load_dotenv
import httpx

load_dotenv()
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",")
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.scanner import process_pdf_upload
from app.pricing import get_prices

app = FastAPI(
    title="OpenShelf API",
    description="Book search, validation, and discovery endpoints for OpenShelf.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
GUTENDEX_SEARCH_URL = "https://gutendex.com/books"
INTERNET_ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
MAX_RESULTS = 10

SUPPORTED_PROVIDERS = [
    "Open Library",
    "Internet Archive",
    "Project Gutenberg",
    "Standard Ebooks",
    "ManyBooks",
    "Feedbooks Public Domain",
    "OAPEN",
    "Directory of Open Access Books",
    "OpenStax",
    "Open Textbook Library",
]

def normalize_authors(authors: Any) -> list[str]:
    if not isinstance(authors, list):
        return ["Unknown author"]
    cleaned = [str(name).strip() for name in authors if str(name).strip()]
    return cleaned or ["Unknown author"]

def build_access(category: str, note: str) -> dict[str, Any]:
    flags = {
        "is_verified_full_book": False,
        "is_borrowable": False,
        "is_preview": False,
        "is_unverified": False,
        "free_download": False,
        "read_online": False,
    }
    
    if category == "FULL_BOOK_VERIFIED_DOWNLOAD":
        flags["is_verified_full_book"] = True
        flags["free_download"] = True
    elif category == "FULL_BOOK_VERIFIED_ONLINE":
        flags["is_verified_full_book"] = True
        flags["read_online"] = True
    elif category == "AUTHORIZED_BORROWING":
        flags["is_borrowable"] = True
    elif category == "PREVIEW":
        flags["is_preview"] = True
    else:
        flags["is_unverified"] = True

    return {
        **flags,
        "category": category,
        "note": note,
    }

def deduplicate_results(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...], str, str]] = set()

    for item in items:
        title_value = str(item.get("title") or "").strip().lower()
        authors = tuple(str(name).strip() for name in item.get("authors", []) if str(name).strip())
        provider_name = str(item.get("provider") or "").strip().lower()
        url_value = str(item.get("source_links", [{}])[0].get("url") if item.get("source_links") else "")
        signature = (title_value, authors, provider_name, url_value)
        if signature in seen:
            continue
        seen.add(signature)
        deduplicated.append(item)

    return deduplicated

async def search_open_library(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={
                "q": query_value,
                "limit": MAX_RESULTS,
                "fields": "key,title,author_name,cover_i,first_publish_year,edition_key,has_fulltext,ia,availability,ebook_access",
            },
        )
        response.raise_for_status()
        payload = response.json()

    docs = payload.get("docs", [])
    results: list[dict[str, Any]] = []
    for item in docs:
        title_value = str(item.get("title") or "").strip()
        if not title_value:
            continue
        authors = normalize_authors(item.get("author_name"))
        cover_i = item.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None

        ia_value = item.get("ia")
        ia_identifier = str(ia_value[0]).strip() if isinstance(ia_value, list) and ia_value else None

        status = str((item.get("availability") or {}).get("status") or "").lower()
        ebook_access = str(item.get("ebook_access") or "").lower()
        has_fulltext = bool(item.get("has_fulltext"))

        source_links = []
        key = item.get("key")
        if key:
            source_links.append({"label": "Open Library", "url": f"https://openlibrary.org{key}"})

        # Classification workflow
        if ebook_access == "public" and has_fulltext:
            access = build_access("FULL_BOOK_VERIFIED_ONLINE", "Verified public domain or open access edition.")
            if ia_identifier:
                source_links.append({"label": "Read on Internet Archive", "url": f"https://archive.org/details/{ia_identifier}"})
        elif "borrow" in status or ebook_access == "borrowable":
            access = build_access("AUTHORIZED_BORROWING", "Complete book requires authorized borrowing via Open Library/Internet Archive.")
        elif ebook_access == "printdisabled":
            access = build_access("AUTHORIZED_BORROWING", "Book available to borrow for print-disabled users.")
        elif "preview" in status or ebook_access == "preview":
            access = build_access("PREVIEW", "Only a short preview or sample is available.")
        elif has_fulltext:
            access = build_access("COMPLETENESS_UNVERIFIED", "Full text flagged, but access rules are not explicitly clear.")
        else:
            access = build_access("COMPLETENESS_UNVERIFIED", "No verified complete edition found.")

        results.append({
            "provider": "Open Library",
            "title": title_value,
            "authors": authors,
            "publication_year": item.get("first_publish_year"),
            "cover_url": cover_url,
            "source_links": source_links,
            "access": access,
        })
    return results

async def search_project_gutenberg(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(GUTENDEX_SEARCH_URL, params={"search": query_value, "page": 1})
        response.raise_for_status()
        payload = response.json()

    books = payload.get("results", [])
    results: list[dict[str, Any]] = []
    for item in books:
        title_value = str(item.get("title") or "").strip()
        if not title_value:
            continue
        authors = normalize_authors(item.get("authors") or [item.get("author")])
        books_link = item.get("formats") or {}
        
        # PG books are definitively full text and free
        html_url = books_link.get("text/html") or books_link.get("text/html; charset=utf-8")
        epub_url = books_link.get("application/epub+zip")
        if isinstance(html_url, dict): html_url = next(iter(html_url.values()), None)
        
        url = html_url or epub_url or f"https://www.gutenberg.org/ebooks/{item.get('id')}"
        
        results.append({
            "provider": "Project Gutenberg",
            "title": title_value,
            "authors": authors,
            "publication_year": None,
            "cover_url": books_link.get("image/jpeg"),
            "source_links": [{"label": "Project Gutenberg Download", "url": str(url)}],
            "access": build_access("FULL_BOOK_VERIFIED_DOWNLOAD", "Verified complete public domain book available for free download."),
        })
    return results

async def search_internet_archive(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(
            INTERNET_ARCHIVE_SEARCH_URL,
            params={
                "q": query_value,
                "rows": 5,
                "fl[]": ["identifier", "title", "creator", "year", "mediatype", "collection", "lending___status", "access-restricted-item"],
                "output": "json",
            },
        )
        response.raise_for_status()
        payload = response.json()

    docs = (payload.get("response") or {}).get("docs", [])
    results: list[dict[str, Any]] = []
    for item in docs:
        title_value = str(item.get("title") or "").strip()
        if not title_value:
            continue
        creator = item.get("creator") or []
        authors = normalize_authors(creator if isinstance(creator, list) else [creator])
        identifier = item.get("identifier")
        url = f"https://archive.org/details/{identifier}" if identifier else "https://archive.org/"
        
        lending_status = item.get("lending___status", "")
        restricted = item.get("access-restricted-item", False)
        
        if lending_status == "is_lendable":
            access = build_access("AUTHORIZED_BORROWING", "Authorized borrowing required.")
        elif restricted:
            access = build_access("AUTHORIZED_BORROWING", "Access is restricted; borrowing or log-in may be required.")
        else:
            access = build_access("FULL_BOOK_VERIFIED_ONLINE", "Verified full text available online.")

        results.append({
            "provider": "Internet Archive",
            "title": title_value,
            "authors": authors,
            "publication_year": item.get("year"),
            "cover_url": f"https://archive.org/services/img/{identifier}" if identifier else None,
            "source_links": [{"label": "Internet Archive", "url": url}],
            "access": access,
        })
    return results

# Fallback generator for sources without suitable/open JSON APIs
def generate_external_search(provider: str, query: str, search_url_template: str) -> dict[str, Any]:
    url = search_url_template.replace("{query}", urllib.parse.quote(query))
    return {
        "provider": provider,
        "title": f"Search '{query}' on {provider}",
        "authors": [f"via {provider}"],
        "publication_year": None,
        "cover_url": None,
        "source_links": [{"label": f"Search {provider}", "url": url}],
        "access": build_access("COMPLETENESS_UNVERIFIED", "Official search link. Completeness varies by result on their site."),
    }

async def get_external_searches(query: str) -> list[dict[str, Any]]:
    return [
        generate_external_search("Standard Ebooks", query, "https://standardebooks.org/ebooks?query={query}"),
        generate_external_search("ManyBooks", query, "https://manybooks.net/search-book?search={query}"),
        generate_external_search("Feedbooks Public Domain", query, "https://www.feedbooks.com/catalog/public_domain?query={query}"),
        generate_external_search("OAPEN", query, "https://library.oapen.org/discover?query={query}"),
        generate_external_search("Directory of Open Access Books", query, "https://directory.doabooks.org/discover?query={query}"),
        generate_external_search("OpenStax", query, "https://openstax.org/search?q={query}"),
        generate_external_search("Open Textbook Library", query, "https://open.umn.edu/opentextbooks/textbooks?term={query}"),
    ]

async def aggregate_provider_results(query_value: str) -> tuple[list[dict[str, Any]], list[str]]:
    providers = [
        ("Open Library", search_open_library),
        ("Project Gutenberg", search_project_gutenberg),
        ("Internet Archive", search_internet_archive),
    ]

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    provider_results = await asyncio.gather(
        *(provider_fn(query_value) for _, provider_fn in providers),
        return_exceptions=True,
    )

    for (provider_name, _), provider_value in zip(providers, provider_results):
        if isinstance(provider_value, Exception):
            errors.append(provider_name)
            continue
        if isinstance(provider_value, list):
            results.extend(provider_value)

    unique_results = deduplicate_results(results)
    unique_results.extend(await get_external_searches(query_value))
    return unique_results, errors

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "OpenShelf backend is running."}

@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "OpenShelf API"}

@app.get("/api/books/search")
async def search_books(
    q: str | None = Query(default=None, description="Book title or author"),
) -> dict[str, Any]:
    query_value = (q or "").strip()
    if not query_value:
        raise HTTPException(status_code=400, detail="A search query is required.")

    try:
        results, provider_errors = await aggregate_provider_results(query_value)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The book search service is unavailable right now.") from exc

    return {
        "query": query_value,
        "count": len(results),
        "results": results,
        "provider_errors": provider_errors,
    }

@app.post("/api/scan")
async def scan_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    return await process_pdf_upload(file)

@app.get("/api/books/prices")
async def fetch_prices(
    q: str | None = Query(default=None, description="Book title or ISBN to search for prices"),
) -> dict[str, Any]:
    query_value = (q or "").strip()
    if not query_value:
        raise HTTPException(status_code=400, detail="A search query or ISBN is required.")

    try:
        pricing_result = await get_prices(query_value)
        return pricing_result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The price comparison service is unavailable right now.") from exc
