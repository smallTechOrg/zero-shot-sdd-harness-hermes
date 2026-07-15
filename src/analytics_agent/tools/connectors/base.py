from abc import ABC, abstractmethod

from analytics_agent.config.settings import Settings, get_settings
from analytics_agent.domain.models import SourceRecord


class BaseConnector(ABC):
    """One source family. `pull()` returns normalized records for the funnel stages."""

    id: str = ""
    name: str = ""
    env_var: str = ""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials this connector needs are present in .env."""

    @abstractmethod
    def pull(self) -> list[SourceRecord]:
        """Return normalized SourceRecords. Must not raise on missing config."""


class SampleConnector(BaseConnector):
    """Default data source. Produces a full, realistic funnel with no credentials.

    The shape is deterministic-ish but varies slightly per call so Refresh shows movement.
    Sample data is always flagged `sample: true` in the API and UI.
    """

    id = "sample"
    name = "Sample Adapter"
    env_var = "(none — default)"

    def is_configured(self) -> bool:
        return True

    def pull(self) -> list[SourceRecord]:
        import random

        top = random.randint(11000, 13000)
        signup = int(top * random.uniform(0.13, 0.17))
        activated = int(signup * random.uniform(0.48, 0.58))
        retained = int(activated * random.uniform(0.58, 0.70))
        revenue = int(retained * random.uniform(0.34, 0.44))
        return [
            SourceRecord(source="sample", stage="visit_or_install", count=top),
            SourceRecord(source="sample", stage="signup", count=signup),
            SourceRecord(source="sample", stage="activated", count=activated),
            SourceRecord(source="sample", stage="retained", count=retained),
            SourceRecord(source="sample", stage="revenue", count=revenue),
        ]
