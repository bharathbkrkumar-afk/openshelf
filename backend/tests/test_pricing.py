import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)

def test_fetch_prices_requires_query():
    response = client.get("/api/books/prices")
    assert response.status_code == 400
    assert "required" in response.json()["detail"]

def test_fetch_prices_returns_search_links(monkeypatch):
    from app import pricing
    
    async def mock_fetch(query): return None
    monkeypatch.setattr(pricing, "fetch_bookswagon", mock_fetch)
    monkeypatch.setattr(pricing, "fetch_crossword", mock_fetch)
    monkeypatch.setattr(pricing, "fetch_sapnaonline", mock_fetch)
    
    response = client.get("/api/books/prices?q=Dune")
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Dune"
    
    # Verify that search links are populated correctly for unsupported retailers
    retailers = [link["retailer"] for link in payload["search_links"]]
    assert "Amazon India" in retailers
    assert "Flipkart" in retailers
    assert "Meesho" in retailers
    assert "BooksWagon" in retailers

    # Verify URLs are correctly encoded
    amazon_link = next(link for link in payload["search_links"] if link["retailer"] == "Amazon India")
    assert "Dune" in amazon_link["url"]

def test_fetch_prices_error_handling(monkeypatch):
    from app import main as app_module
    
    async def fake_get_prices(query):
        raise RuntimeError("Service failure")
        
    monkeypatch.setattr(app_module, "get_prices", fake_get_prices)
    
    response = client.get("/api/books/prices?q=Dune")
    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]
