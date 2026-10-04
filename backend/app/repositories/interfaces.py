from abc import ABC, abstractmethod
from typing import List, Optional, Any

class IEventRepository(ABC):
    @abstractmethod
    def add(self, event: Any) -> None:
        pass

    @abstractmethod
    def get(self, event_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[Any]:
        pass

    @abstractmethod
    def get_total_count(self, **filters) -> int:
        pass

class IAlertRepository(ABC):
    @abstractmethod
    def add(self, alert: Any) -> None:
        pass

    @abstractmethod
    def get(self, alert_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def update(self, alert: Any) -> None:
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[Any]:
        pass
        
    @abstractmethod
    def get_total_count(self, **filters) -> int:
        pass
