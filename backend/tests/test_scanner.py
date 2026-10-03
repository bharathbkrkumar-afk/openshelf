import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app import scanner

client = TestClient(app)

def test_scan_requires_pdf():
    response = client.post("/api/scan", files={"file": ("test.txt", b"hello world", "text/plain")})
    assert response.status_code == 200
    assert response.json()["status"] == "SCAN_FAILED"
    assert "must be a PDF" in response.json()["message"]

def test_scan_empty_file():
    response = client.post("/api/scan", files={"file": ("test.pdf", b"", "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "SCAN_FAILED"
    assert "empty" in response.json()["message"]

def test_scan_invalid_signature():
    response = client.post("/api/scan", files={"file": ("test.pdf", b"MZ\x90\x00\x03\x00not a pdf", "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "SCAN_FAILED"
    assert "Invalid PDF signature" in response.json()["message"]

def test_oversized_file(monkeypatch):
    monkeypatch.setattr(scanner, "MAX_FILE_SIZE", 10)
    response = client.post("/api/scan", files={"file": ("test.pdf", b"%PDF-1.4\n1234567890", "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "SCAN_FAILED"
    assert "exceeds maximum allowed size" in response.json()["message"]

def test_malformed_pdf_structure(monkeypatch):
    # This is a valid signature but invalid structure for PyPDF
    pdf_content = b"%PDF-1.4\n%EOF\n"
    response = client.post("/api/scan", files={"file": ("test.pdf", pdf_content, "application/pdf")})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUSPICIOUS_INDICATORS"
    assert "Malformed or corrupted" in str(data["indicators"])

def test_clamav_unavailable_returns_safe_structure(monkeypatch):
    def fake_inspect(path): return True, []
    def fake_clamav(): return False
    
    monkeypatch.setattr(scanner, "inspect_pdf_structure", fake_inspect)
    monkeypatch.setattr(scanner, "check_clamav_available", fake_clamav)

    pdf_content = b"%PDF-1.4\n%Fake Valid Content"
    response = client.post("/api/scan", files={"file": ("test.pdf", pdf_content, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "SCANNER_UNAVAILABLE"

def test_clamav_threat_detected(monkeypatch):
    def fake_inspect(path): return True, []
    def fake_clamav(): return True
    def fake_scan(path): return False, "Threat detected: EICAR"
    
    monkeypatch.setattr(scanner, "inspect_pdf_structure", fake_inspect)
    monkeypatch.setattr(scanner, "check_clamav_available", fake_clamav)
    monkeypatch.setattr(scanner, "scan_with_clamav", fake_scan)

    pdf_content = b"%PDF-1.4\n%Fake Valid Content"
    response = client.post("/api/scan", files={"file": ("test.pdf", pdf_content, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "THREATS_DETECTED"
    assert "EICAR" in response.json()["message"]

def test_safe_pdf(monkeypatch):
    def fake_inspect(path): return True, []
    def fake_clamav(): return True
    def fake_scan(path): return True, "No threats detected by ClamAV."
    
    monkeypatch.setattr(scanner, "inspect_pdf_structure", fake_inspect)
    monkeypatch.setattr(scanner, "check_clamav_available", fake_clamav)
    monkeypatch.setattr(scanner, "scan_with_clamav", fake_scan)

    pdf_content = b"%PDF-1.4\n%Fake Valid Content"
    response = client.post("/api/scan", files={"file": ("test.pdf", pdf_content, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "NO_THREATS_DETECTED"
