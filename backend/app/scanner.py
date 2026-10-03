import os
import shutil
import subprocess
import tempfile
import hashlib
from typing import Any
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from fastapi import UploadFile

from dotenv import load_dotenv
load_dotenv()

MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 50 * 1024 * 1024))  # 50 MB

def check_clamav_available() -> bool:
    try:
        result = subprocess.run(["clamscan", "--version"], capture_output=True, text=True, timeout=2)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def scan_with_clamav(file_path: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["clamscan", "--no-summary", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "No threats detected by ClamAV."
        elif result.returncode == 1:
            return False, f"Threat detected: {result.stdout.strip()}"
        else:
            return False, "ClamAV scan failed."
    except Exception as e:
        return False, f"ClamAV execution error: {str(e)}"

def inspect_pdf_structure(file_path: str) -> tuple[bool, list[str]]:
    suspicious_indicators = []
    try:
        reader = PdfReader(file_path)
        
        # Check if encrypted
        if reader.is_encrypted:
            suspicious_indicators.append("File is encrypted. Cannot fully inspect contents.")
            return False, suspicious_indicators

        # Look for JavaScript or Launch Actions in catalog
        catalog = reader.trailer.get("/Root", {}).get_object()
        if not catalog:
            return True, []

        names = catalog.get("/Names", {}).get_object()
        if names:
            javascript = names.get("/JavaScript")
            if javascript:
                suspicious_indicators.append("JavaScript embedded in PDF.")
            embedded = names.get("/EmbeddedFiles")
            if embedded:
                suspicious_indicators.append("Embedded files found in PDF.")

        # Iterate over pages to find suspicious annotations (Launch, JavaScript)
        for i, page in enumerate(reader.pages):
            annots = page.get("/Annots")
            if annots:
                for annot in annots:
                    annot_obj = annot.get_object()
                    action = annot_obj.get("/A", {}).get_object()
                    if action:
                        action_type = action.get("/S")
                        if action_type == "/JavaScript":
                            suspicious_indicators.append(f"JavaScript action found on page {i+1}.")
                        elif action_type == "/Launch":
                            suspicious_indicators.append(f"Launch action found on page {i+1}.")

    except PyPdfError as e:
        suspicious_indicators.append("Malformed or corrupted PDF structure.")
    except Exception as e:
        suspicious_indicators.append(f"Error parsing PDF: {str(e)}")

    has_suspicious = len(suspicious_indicators) > 0
    return not has_suspicious, suspicious_indicators

async def process_pdf_upload(file: UploadFile) -> dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "SCAN_FAILED", "message": "File must be a PDF."}

    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    file_hash = hashlib.sha256()
    
    try:
        file_size = 0
        signature_checked = False
        
        with os.fdopen(temp_fd, "wb") as out_file:
            while chunk := await file.read(8192):
                if not signature_checked:
                    if not chunk.startswith(b"%PDF-"):
                        return {"status": "SCAN_FAILED", "message": "Invalid PDF signature."}
                    signature_checked = True
                
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    return {"status": "SCAN_FAILED", "message": f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB."}
                
                out_file.write(chunk)
                file_hash.update(chunk)
        
        if file_size == 0:
            return {"status": "SCAN_FAILED", "message": "File is empty."}
            
        sha256_hex = file_hash.hexdigest()
        
        # Structure Check
        structure_safe, indicators = inspect_pdf_structure(temp_path)
        if not structure_safe:
            return {
                "status": "SUSPICIOUS_INDICATORS",
                "message": "Suspicious features or malformed structure detected.",
                "indicators": indicators,
                "sha256": sha256_hex
            }
            
        # ClamAV Check
        clamav_available = check_clamav_available()
        if not clamav_available:
            return {
                "status": "SCANNER_UNAVAILABLE",
                "message": "ClamAV scanner is not available on this system. Structural check passed.",
                "sha256": sha256_hex
            }
            
        is_safe, clam_msg = scan_with_clamav(temp_path)
        if not is_safe:
            return {
                "status": "THREATS_DETECTED",
                "message": clam_msg,
                "sha256": sha256_hex
            }
            
        return {
            "status": "NO_THREATS_DETECTED",
            "message": "No threats detected by structure check or ClamAV. Note: No scan guarantees complete safety.",
            "sha256": sha256_hex
        }

    except Exception as e:
        return {"status": "SCAN_FAILED", "message": f"An unexpected error occurred during scanning: {str(e)}"}
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
