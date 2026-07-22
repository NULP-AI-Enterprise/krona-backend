from pathlib import Path
from charset_normalizer import from_path
from .base_reader import IFileReaderStrategy

class TxtReader(IFileReaderStrategy):
    def read(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found at {file_path}")
            return ""
        try:
            result = from_path(path).best()
            if result is None:
                print(f"Error: Unable to determine encoding for {file_path}.")
                return ""
            return str(result)
        except Exception as e:
            print(f"Error reading TXT file {file_path}: {e}")
            return ""
