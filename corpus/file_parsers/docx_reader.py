import docx2txt
from pathlib import Path
from .base_reader import IFileReaderStrategy

class DocxReader(IFileReaderStrategy):
    def read(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found at {file_path}")
            return ""
        try:
            text = docx2txt.process(path)
            return text
        except Exception as e:
            print(f"Error reading DOCX file {file_path}: {e}")
            return ""
