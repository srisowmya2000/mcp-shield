from abc import ABC, abstractmethod
from runtime.models import RunConfig, SandboxStatus

class SandboxBackend(ABC):
    @abstractmethod
    def launch(self, config: RunConfig) -> SandboxStatus:
        pass

    @abstractmethod
    def stop(self, server_name: str) -> dict:
        pass

    @abstractmethod
    def list_running(self) -> list[dict]:
        pass
