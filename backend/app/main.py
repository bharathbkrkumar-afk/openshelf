from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="OpenShelf API",
    description="Book search, validation, and discovery endpoints for OpenShelf.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0):(?:\d+)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_SEARCH_URL = "https://www.googleapis.com/books/v1/volumes"
GUTENDEX_SEARCH_URL = "https://gutendex.com/books"
INTERNET_ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
MAX_RESULTS = 10
SUPPORTED_PROVIDERS = [
    "Open Library",
    "Google Books",
    "Project Gutenberg",
    "Internet Archive",
]


def normalize_authors(authors: Any) -> list[str]:
    if not isinstance(authors, list):
        return ["Unknown author"]
    cleaned = [str(name).strip() for name in authors if str(name).strip()]
    return cleaned or ["Unknown author"]


def build_access(access_type: str, custom_note: str | None = None) -> dict[str, Any]:
    if access_type == "full_text":
        note = custom_note or "Full text is available from a supported source."
    elif access_type == "preview":
        note = custom_note or "Preview is available from a supported source."
    else:
        note = custom_note or "No suitable free full-text version was found from our supported sources."

    return {
        "full_text": access_type == "full_text",
        "preview": access_type == "preview",
        "note": note,
    }


def build_source_links(book: dict[str, Any], provider: str = "Open Library") -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    url = book.get("url") or book.get("preview_url") or book.get("openlibrary_url")
    if provider == "Open Library":
        key = book.get("key")
        if key:
            links.append({"label": "Open Library", "url": f"https://openlibrary.org{key}"})
        edition_key = book.get("edition_key")
        if isinstance(edition_key, list) and edition_key:
            first_edition = edition_key[0]
            if first_edition:
                links.append(
                    {
                        "label": "Edition",
                        "url": f"https://openlibrary.org/books/{first_edition}",
                    }
                )
    elif url:
        links.append({"label": provider, "url": str(url)})

    if provider == "Open Library" and not links and url:
        links.append({"label": provider, "url": str(url)})

    deduplicated: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for link in links:
        url_value = link["url"]
        if url_value not in seen_urls:
            seen_urls.add(url_value)
            deduplicated.append(link)
    return deduplicated


def classify_access(item: dict[str, Any]) -> dict[str, Any]:
    availability = item.get("availability") if isinstance(item.get("availability"), dict) else {}
    status = str(availability.get("status") or "").lower()
    has_fulltext = bool(item.get("has_fulltext")) or bool(item.get("ia"))
    preview = "preview" in status or "limited" in status

    if has_fulltext:
        return build_access("full_text")
    if preview:
        return build_access("preview")
    return build_access("unavailable")


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
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={
                "q": query_value,
                "limit": MAX_RESULTS,
                "fields": "key,title,author_name,cover_i,first_publish_year,edition_key,has_fulltext,ia,availability",
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
        cover_url = None
        if cover_i:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg"

        ia_value = item.get("ia")
        ia_identifier = None
        if isinstance(ia_value, list) and ia_value:
            ia_identifier = str(ia_value[0]).strip()
        elif isinstance(ia_value, str) and ia_value.strip():
            ia_identifier = ia_value.strip()

        status = str((item.get("availability") or {}).get("status") or "").lower()
        source_links = build_source_links(item, "Open Library")
        if ia_identifier:
            source_links.append({"label": "Internet Archive", "url": f"https://archive.org/details/{ia_identifier}"})
            source_links = list({link["url"]: link for link in source_links}.values())
            access = build_access("full_text", "Full text is available from Internet Archive.")
        elif "preview" in status or "limited" in status:
            access = build_access("preview", "Preview is available from Open Library.")
        else:
            access = build_access("unavailable")

        result = {
            "provider": "Open Library",
            "title": title_value,
            "authors": authors,
            "publication_year": item.get("first_publish_year"),
            "cover_url": cover_url,
            "key": item.get("key"),
            "edition_key": item.get("edition_key"),
            "source_links": source_links,
            "access": access,
        }
        results.append(result)
    return results


async def search_google_books(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        try:
            response = await client.get(
                GOOGLE_BOOKS_SEARCH_URL,
                params={"q": query_value, "maxResults": 5},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                return []
            raise

    items = payload.get("items", [])
    results: list[dict[str, Any]] = []
    for item in items:
        volume_info = item.get("volumeInfo") or {}
        title_value = str(volume_info.get("title") or "").strip()
        if not title_value:
            continue
        authors = normalize_authors(volume_info.get("authors"))
        access_info = item.get("accessInfo") or {}
        viewability = str(access_info.get("viewability") or "").upper()
        access_view_status = str(access_info.get("accessViewStatus") or "").upper()
        preview_link = access_info.get("webReaderLink") or access_info.get("previewLink")
        if access_view_status in {"FULL_PUBLIC_DOMAIN", "FULLY_AVAILABLE"}:
            access_type = "full_text"
            note = "Full text is available from Google Books."
        elif viewability in {"PARTIAL", "ALL_PAGES", "SAMPLE"} or bool(preview_link):
            access_type = "preview"
            note = "Preview is available from Google Books."
        else:
            access_type = "unavailable"
            note = "No suitable free full-text version was found from our supported sources."

        results.append(
            {
                "provider": "Google Books",
                "title": title_value,
                "authors": authors,
                "publication_year": volume_info.get("publishedDate")[:4] if isinstance(volume_info.get("publishedDate"), str) and volume_info.get("publishedDate") else None,
                "cover_url": (volume_info.get("imageLinks") or {}).get("thumbnail"),
                "source_links": [{"label": "Google Books", "url": str(preview_link or item.get("selfLink") or "")}],
                "access": build_access(access_type, note),
            }
        )
    return results


async def search_project_gutenberg(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        response = await client.get(
            GUTENDEX_SEARCH_URL,
            params={"search": query_value, "page": 1},
        )
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
        html_url = books_link.get("text/html") or books_link.get("text/html; charset=utf-8")
        if isinstance(html_url, dict):
            html_url = next(iter(html_url.values()), None)
        url = html_url or f"https://www.gutenberg.org/ebooks/{item.get('id')}"
        results.append(
            {
                "provider": "Project Gutenberg",
                "title": title_value,
                "authors": authors,
                "publication_year": item.get("bookshelves") and item.get("bookshelves")[0],
                "cover_url": None,
                "source_links": [{"label": "Project Gutenberg", "url": str(url)}],
                "access": build_access("full_text", "Full text is available from Project Gutenberg."),
            }
        )
    return results


async def search_internet_archive(query_value: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        response = await client.get(
            INTERNET_ARCHIVE_SEARCH_URL,
            params={
                "q": query_value,
                "rows": 5,
                "fl[]": ["identifier", "title", "creator", "year", "mediatype", "collection"],
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
        mediatype = str(item.get("mediatype") or "").lower()
        collection = item.get("collection") or []
        has_text = mediatype == "texts" or "texts" in str(collection).lower()
        if has_text:
            access_type = "full_text"
            note = "Full text is available from Internet Archive."
        else:
            access_type = "unavailable"
            note = "No suitable free full-text version was found from our supported sources."

        url = f"https://archive.org/details/{identifier}" if identifier else "https://archive.org/"
        results.append(
            {
                "provider": "Internet Archive",
                "title": title_value,
                "authors": authors,
                "publication_year": item.get("year"),
                "cover_url": None,
                "source_links": [{"label": "Internet Archive", "url": url}],
                "access": build_access(access_type, note),
            }
        )
    return results


async def aggregate_provider_results(query_value: str) -> tuple[list[dict[str, Any]], list[str]]:
    providers = [
        ("Open Library", search_open_library),
        ("Google Books", search_google_books),
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
    return unique_results, errors


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "OpenShelf backend is running."}


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "OpenShelf API",
        "message": "The backend foundation is ready for milestone 2.",
    }


@app.get("/api/books/search")
async def search_books(
    q: str | None = Query(default=None, description="Book title or author"),
    title: str | None = None,
    author: str | None = None,
) -> dict[str, Any]:
    query_value = (q or title or author or "").strip()
    if title and author:
        query_value = f"{title} {author}".strip()
    elif title:
        query_value = title.strip()
    elif author:
        query_value = author.strip()

    if not query_value:
        raise HTTPException(status_code=400, detail="A search query is required.")

    try:
        results, provider_errors = await aggregate_provider_results(query_value)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The book search service is unavailable right now.",
        ) from exc

    if not results and provider_errors and len(provider_errors) >= len(SUPPORTED_PROVIDERS):
        raise HTTPException(
            status_code=502,
            detail="The book search service is unavailable right now.",
        )

    return {
        "query": query_value,
        "count": len(results),
        "results": results,
        "provider_errors": provider_errors,
    }
