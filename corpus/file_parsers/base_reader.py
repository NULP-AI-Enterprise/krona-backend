from abc import ABC, abstractmethod

class IFileReaderStrategy(ABC):
    """
    Interface (Abstract Base Class) for all file reading strategies.
    It defines the 'contract' that every concrete reader must follow.
    """

    @abstractmethod
    def read(self, file_path: str) -> str:
        """
        Reads a file and returns its content as a single string.
        """
        pass
