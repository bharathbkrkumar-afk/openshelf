import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main as app_module
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "OpenShelf API"
    assert "milestone" in payload["message"].lower()

    response = client.get("/api/health")
    assert response.status_code == 200


def test_search_requires_query() -> None:
    response = client.get("/api/books/search")
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"] == "A search query is required."


def test_whitespace_query_is_rejected() -> None:
    response = client.get("/api/books/search?q=%20%20")
    assert response.status_code == 400
    assert response.json()["detail"] == "A search query is required."


def test_title_search_returns_results() -> None:
    response = client.get("/api/books/search?q=Pride and Prejudice")
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Pride and Prejudice"
    assert payload["count"] >= 1
    assert len(payload["results"]) >= 1
    first_result = payload["results"][0]
    assert first_result["title"]
    assert "authors" in first_result
    assert "source_links" in first_result
    assert "access" in first_result


def test_author_search_returns_results() -> None:
    response = client.get("/api/books/search?author=George Orwell")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert payload["results"][0]["authors"]


def test_no_results_returns_empty_list() -> None:
    response = client.get("/api/books/search?q=xyzabc123notarealbook")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["results"] == []


def test_missing_metadata_is_handled_gracefully(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/missing-metadata",
                            "title": None,
                            "author_name": None,
                            "has_fulltext": False,
                            "edition_key": ["edition-1"],
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=missing metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0


def test_duplicate_results_are_deduplicated(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/example-1",
                            "title": "Duplicate Title",
                            "author_name": ["Example Author"],
                            "edition_key": ["edition-1"],
                            "first_publish_year": 2020,
                            "has_fulltext": True,
                            "ia": ["book-1"],
                        },
                        {
                            "key": "/works/example-1",
                            "title": "Duplicate Title",
                            "author_name": ["Example Author"],
                            "edition_key": ["edition-1"],
                            "first_publish_year": 2020,
                            "has_fulltext": True,
                            "ia": ["book-1"],
                        },
                        {
                            "key": "/works/example-2",
                            "title": "Different Title",
                            "author_name": ["Example Author"],
                            "edition_key": ["edition-2"],
                            "first_publish_year": 2021,
                            "has_fulltext": False,
                        },
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=duplicate title")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 2


def test_full_text_preview_and_unavailable_are_classified(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/full-text-example",
                            "title": "Full Text Title",
                            "author_name": ["Full Text Author"],
                            "has_fulltext": True,
                            "ia": ["book-ia"],
                            "edition_key": ["edition-full"],
                        },
                        {
                            "key": "/works/preview-example",
                            "title": "Preview Title",
                            "author_name": ["Preview Author"],
                            "availability": {"status": "preview"},
                            "edition_key": ["edition-preview"],
                        },
                        {
                            "key": "/works/unavailable-example",
                            "title": "Unavailable Title",
                            "author_name": ["Unavailable Author"],
                            "availability": {"status": "restricted"},
                            "edition_key": ["edition-unavailable"],
                        },
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=test classification")
    assert response.status_code == 200
    payload = response.json()
    access_by_title = {item["title"]: item["access"] for item in payload["results"]}
    assert access_by_title["Full Text Title"]["full_text"] is True
    assert access_by_title["Preview Title"]["preview"] is True
    assert access_by_title["Unavailable Title"]["full_text"] is False
    assert "borrow" not in access_by_title["Full Text Title"]
    assert "borrow" not in access_by_title["Preview Title"]
    assert "borrow" not in access_by_title["Unavailable Title"]


def test_no_suitable_full_text_note_when_none_available(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/restricted",
                            "title": "Restricted Title",
                            "author_name": ["Restricted Author"],
                            "availability": {"status": "restricted"},
                            "edition_key": ["edition-restricted"],
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=restricted book")
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["access"]["full_text"] is False
    assert payload["results"][0]["access"]["note"] == (
        "No suitable free full-text version was found from our supported sources."
    )


def test_api_error_returns_502(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=Pride and Prejudice")
    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"].lower()


def test_multiple_providers_are_combined(monkeypatch) -> None:
    async def fake_open_library(query_value):
        return [
            {
                "provider": "Open Library",
                "title": "Example Book",
                "authors": ["Example Author"],
                "publication_year": 2020,
                "source_links": [{"label": "Open Library", "url": "https://example.com/open"}],
                "access": {"full_text": True, "preview": False, "note": "Full text is available from a supported source."},
            }
        ]

    async def fake_google_books(query_value):
        return [
            {
                "provider": "Google Books",
                "title": "Example Book",
                "authors": ["Example Author"],
                "publication_year": 2021,
                "source_links": [{"label": "Google Books", "url": "https://example.com/google"}],
                "access": {"full_text": False, "preview": True, "note": "Preview is available from Google Books."},
            }
        ]

    async def fake_gutenberg(query_value):
        return []

    async def fake_ia(query_value):
        return []

    monkeypatch.setattr(app_module, "search_open_library", fake_open_library)
    monkeypatch.setattr(app_module, "search_google_books", fake_google_books)
    monkeypatch.setattr(app_module, "search_project_gutenberg", fake_gutenberg)
    monkeypatch.setattr(app_module, "search_internet_archive", fake_ia)

    response = client.get("/api/books/search?q=example book")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    providers = {item["provider"] for item in payload["results"]}
    assert {"Open Library", "Google Books"}.issubset(providers)


def test_provider_error_does_not_break_other_providers(monkeypatch) -> None:
    async def fake_open_library(query_value):
        raise RuntimeError("open library failed")

    async def fake_google_books(query_value):
        return [
            {
                "provider": "Google Books",
                "title": "Fallback Book",
                "authors": ["Fallback Author"],
                "publication_year": 2022,
                "source_links": [{"label": "Google Books", "url": "https://example.com/fallback"}],
                "access": {"full_text": False, "preview": True, "note": "Preview is available from Google Books."},
            }
        ]

    async def fake_gutenberg(query_value):
        return []

    async def fake_ia(query_value):
        return []

    monkeypatch.setattr(app_module, "search_open_library", fake_open_library)
    monkeypatch.setattr(app_module, "search_google_books", fake_google_books)
    monkeypatch.setattr(app_module, "search_project_gutenberg", fake_gutenberg)
    monkeypatch.setattr(app_module, "search_internet_archive", fake_ia)

    response = client.get("/api/books/search?q=fallback book")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["provider_errors"] == ["Open Library"]


def test_full_pdf_available_sets_verified_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "items": [
                        {
                            "volumeInfo": {
                                "title": "Full PDF Book",
                                "authors": ["Author One"],
                                "publishedDate": "2024-01-01",
                            },
                            "accessInfo": {
                                "viewability": "ALL_PAGES",
                                "pdf": {"isAvailable": True, "downloadLink": "https://example.com/full.pdf"},
                                "epub": {"isAvailable": False},
                                "webReaderLink": "https://books.google.com/books?id=abc",
                            },
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=full pdf book")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["full_text_available"] is True
    assert access["preview_only"] is False
    assert access["no_verified_full_text"] is False


def test_google_books_preview_only_is_not_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "items": [
                        {
                            "volumeInfo": {"title": "Preview Only Book", "authors": ["Preview Author"]},
                            "accessInfo": {
                                "viewability": "PARTIAL",
                                "pdf": {"isAvailable": False},
                                "epub": {"isAvailable": False},
                                "webReaderLink": "https://books.google.com/books?id=preview",
                            },
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=preview book")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["full_text_available"] is False
    assert access["preview_only"] is True
    assert access["no_verified_full_text"] is False


def test_google_books_all_pages_without_download_link_is_preview_not_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "items": [
                        {
                            "volumeInfo": {"title": "Misleading Google Book", "authors": ["Author"]},
                            "accessInfo": {
                                "viewability": "ALL_PAGES",
                                "pdf": {"isAvailable": True},
                                "epub": {"isAvailable": False},
                                "webReaderLink": "https://books.google.com/books?id=misleading",
                            },
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=misleading")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["full_text_available"] is False
    assert access["preview_only"] is True


def test_metadata_catalog_only_is_not_verified_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/catalog-only",
                            "title": "Catalog Only Book",
                            "author_name": ["Catalog Author"],
                            "availability": {"status": "restricted"},
                            "edition_key": ["edition-catalog"],
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=catalog only")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["full_text_available"] is False
    assert access["preview_only"] is False
    assert access["no_verified_full_text"] is True


def test_borrow_only_access_is_not_free_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "docs": [
                        {
                            "key": "/works/borrow-only",
                            "title": "Borrow Only Book",
                            "author_name": ["Borrow Author"],
                            "availability": {"status": "borrow_available"},
                            "edition_key": ["edition-borrow"],
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=borrow only")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["borrow_available"] is True
    assert access["full_text_available"] is False
    assert access["preview_only"] is False


def test_missing_or_ambiguous_availability_does_not_assume_full_text(monkeypatch) -> None:
    async def fake_get(self, *args, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "items": [
                        {
                            "volumeInfo": {"title": "Ambiguous Book", "authors": ["Ambiguous Author"]},
                            "accessInfo": {},
                        }
                    ]
                }

        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.get("/api/books/search?q=ambiguous")
    assert response.status_code == 200
    payload = response.json()
    access = payload["results"][0]["access"]
    assert access["full_text_available"] is False
    assert access["no_verified_full_text"] is True
    assert access["preview_only"] is False
