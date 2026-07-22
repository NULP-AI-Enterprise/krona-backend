import json
from pathlib import Path

from corpus.file_parsers.base_reader import IFileReaderStrategy
from corpus.file_parsers.txt_reader import TxtReader
from corpus.file_parsers.docx_reader import DocxReader
from corpus.file_parsers.xml_reader import XmlReader
from corpus.file_parsers.pdf_reader import PdfReader
from corpus.file_parsers.csv_reader import CsvReader



class FileProcessorContext:
    """
    The Context class (Strategy Pattern).
    Manages all file reading strategies.
    """
    def __init__(self, strategies: dict[str, IFileReaderStrategy]):
        self._strategies = strategies

    def process_file(self, file_path: str, original_filename: str):
        """
        Main manager function.
        Defines file type and chooses the strategy.
        Returns (content, metadata)
        """
        extension = Path(original_filename).suffix.lower()
        strategy = self._strategies.get(extension)


        metadata = {
            "text_id_user": Path(original_filename).stem,
            "author": "Unknown",
            "genre": "Unknown",
            "source": original_filename
        }

        try:
            if extension == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                content = data.get("content", "")
                metadata.update(data.get("metadata", {}))

            elif strategy:
                content = strategy.read(file_path)

            else:
                raise ValueError(f"Непідтримуваний тип файлу: {original_filename}")

            return content, metadata

        except Exception as e:
            print(f"Помилка парсингу файлу {original_filename}: {e}")
            raise ValueError(f"Помилка парсингу: {e}")


registered_strategies = {
    ".txt": TxtReader(),
    ".docx": DocxReader(),
    ".pdf": PdfReader(),
    ".xml": XmlReader(),
    ".csv": CsvReader(),
}


_file_processor_instance = FileProcessorContext(strategies=registered_strategies)


def parse_uploaded_file(file_path: str, original_filename: str):
    """
    Public facade that calls our singleton-processor.
    search_manager.py depends only on this method.
    """
    return _file_processor_instance.process_file(file_path, original_filename)
