import xml.etree.ElementTree as ET
from pathlib import Path
from .base_reader import IFileReaderStrategy

class XmlReader(IFileReaderStrategy):
    def read(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found at {file_path}")
            return ""
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            text = " ".join(root.itertext())
            return " ".join(text.split())
        except Exception as e:
            print(f"Error reading XML file {file_path}: {e}")
            return ""
