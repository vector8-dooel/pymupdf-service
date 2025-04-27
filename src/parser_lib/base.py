from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file: bytes, executor: ProcessPoolExecutor) -> bytes:
        raise NotImplementedError
