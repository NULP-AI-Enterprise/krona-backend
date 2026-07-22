import pdfplumber
from .base_reader import IFileReaderStrategy
import os

class PdfReader(IFileReaderStrategy):
    def read(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return ""
        all_text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text += page_text + "\n"
            return all_text.strip()
        except Exception as e:
            print(f"Error reading PDF file {file_path}: {e}")
            return ""
