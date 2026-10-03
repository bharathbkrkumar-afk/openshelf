import sys
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main as app_module
from app.main import app

client = TestClient(app)

def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_search_requires_query() -> None:
    response = client.get("/api/books/search")
    assert response.status_code == 400
    assert response.json()["detail"] == "A search query is required."

def test_whitespace_query_is_rejected() -> None:
    response = client.get("/api/books/search?q=%20%20")
    assert response.status_code == 400

def test_title_search_returns_results(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self): return None
            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/123",
                            "title": "Pride and Prejudice",
                            "author_name": ["Jane Austen"],
                            "has_fulltext": True,
                            "ebook_access": "public"
                        }
                    ]
                }
        return Response()
    
    async def fake_empty(query): return []
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(app_module, "search_project_gutenberg", fake_empty)
    monkeypatch.setattr(app_module, "search_internet_archive", fake_empty)

    response = client.get("/api/books/search?q=Pride and Prejudice")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    first = payload["results"][0]
    assert first["title"] == "Pride and Prejudice"
    assert first["access"]["is_verified_full_book"] is True

def test_api_error_returns_502(monkeypatch) -> None:
    async def fake_aggregate(query):
        raise RuntimeError("boom")
    monkeypatch.setattr(app_module, "aggregate_provider_results", fake_aggregate)
    
    response = client.get("/api/books/search?q=Pride and Prejudice")
    assert response.status_code == 502

def test_provider_error_does_not_break_others(monkeypatch) -> None:
    async def fake_open_library(query):
        raise RuntimeError("OL is down")
    
    async def fake_gutenberg(query):
        return [{
            "provider": "Project Gutenberg",
            "title": "Fallback Book",
            "authors": ["Author"],
            "source_links": [],
            "access": app_module.build_access("FULL_BOOK_VERIFIED_DOWNLOAD", "")
        }]

    async def fake_ia(query):
        return []

    monkeypatch.setattr(app_module, "search_open_library", fake_open_library)
    monkeypatch.setattr(app_module, "search_project_gutenberg", fake_gutenberg)
    monkeypatch.setattr(app_module, "search_internet_archive", fake_ia)

    response = client.get("/api/books/search?q=fallback")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_errors"] == ["Open Library"]
    assert len(payload["results"]) > 0

def test_completeness_rules(monkeypatch) -> None:
    async def fake_open_library(query):
        return [
            {
                "provider": "Open Library",
                "title": "Preview Only",
                "authors": ["Author"],
                "source_links": [],
                "access": app_module.build_access("PREVIEW", "")
            },
            {
                "provider": "Open Library",
                "title": "Unverified Book",
                "authors": ["Author"],
                "source_links": [],
                "access": app_module.build_access("COMPLETENESS_UNVERIFIED", "")
            }
        ]
    async def fake_empty(query): return []
    monkeypatch.setattr(app_module, "search_open_library", fake_open_library)
    monkeypatch.setattr(app_module, "search_project_gutenberg", fake_empty)
    monkeypatch.setattr(app_module, "search_internet_archive", fake_empty)
    
    response = client.get("/api/books/search?q=test")
    payload = response.json()
    
    # We should also see 7 external searches
    assert len(payload["results"]) == 9
    
    preview = next(r for r in payload["results"] if r["title"] == "Preview Only")
    assert preview["access"]["is_preview"] is True
    assert preview["access"]["is_verified_full_book"] is False
    
    unverified = next(r for r in payload["results"] if r["title"] == "Unverified Book")
    assert unverified["access"]["is_unverified"] is True
    assert unverified["access"]["is_verified_full_book"] is False

    # check external searches
    external = next(r for r in payload["results"] if r["provider"] == "Standard Ebooks")
    assert external["access"]["is_unverified"] is True
