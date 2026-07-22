import os
import pandas as pd
from .base_reader import IFileReaderStrategy

class CsvReader(IFileReaderStrategy):
    def read(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return ""
        try:
            df = pd.read_csv(file_path, header=None)
            all_values = df.values.flatten()
            all_texts = []
            for item in all_values:
                if pd.isna(item):
                    continue
                text = str(item).strip()
                if text:
                    all_texts.append(text)
            return " ".join(all_texts)
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
            return ""
