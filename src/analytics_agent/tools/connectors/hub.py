from analytics_agent.config.settings import Settings, get_settings
from analytics_agent.domain.models import ConnectorStatus, SetupStep, SourceRecord
from analytics_agent.tools.connectors.base import BaseConnector, SampleConnector
from analytics_agent.tools.connectors.real import build_connectors

__all__ = ["ConnectorHub"]


class ConnectorHub:
    """Resolves the data source: sample adapter by default, real connectors when configured."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.sample = SampleConnector(self.settings)
        self.real = build_connectors(self.settings)

    def statuses(self) -> list[ConnectorStatus]:
        return [
            ConnectorStatus(
                id=c.id, name=c.name, configured=c.is_configured(), env_var=c.env_var
            )
            for c in self.real
        ]

    def setup_guide(self, source_id: str) -> list[SetupStep]:
        guides = {
            "ga4": [
                SetupStep(
                    title="Create a GA4 property",
                    detail="In Google Analytics, create a property for #local (web + app data streams).",
                ),
                SetupStep(
                    title="Get the Property ID",
                    detail="Settings → Property → Property details → copy the Measurement ID / Property ID.",
                ),
                SetupStep(
                    title="Create a service-account key",
                    detail="Google Cloud → IAM → Service Accounts → create key (JSON). Grant 'Viewer' on the GA4 property.",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="GA4_PROPERTY_ID=<property id>\nGA4_CREDENTIALS_JSON=<paste the full service-account JSON>",
                ),
            ],
            "business_db": [
                SetupStep(
                    title="Locate the app database",
                    detail="Find the DB that stores signups, orders, and revenue for #local.",
                ),
                SetupStep(
                    title="Build a read-only connection string",
                    detail="Use a read-only role. Example: postgresql://readonly:***@host:5432/local_app",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="BUSINESS_DB_URL=<your connection string>",
                ),
            ],
            "play_store": [
                SetupStep(
                    title="Google Play Console",
                    detail="Open the Play Console for the #local app.",
                ),
                SetupStep(
                    title="Service account JSON",
                    detail="Play Console → Users & permissions → Invite service account with 'View' access; download the JSON.",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="PLAY_STORE_CREDENTIALS_JSON=<paste the service-account JSON>",
                ),
            ],
            "app_store": [
                SetupStep(
                    title="App Store Connect API key",
                    detail="Users & Access → Keys → create an App Store Connect API key (Key Type: App Manager or read-only).",
                ),
                SetupStep(
                    title="Download the .p8",
                    detail="Download the private key file (AuthKey_XXXX.p8).",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="APPSTORE_CONNECT_KEY_ID=<key id>\nAPPSTORE_CONNECT_ISSUER_ID=<issuer id>\nAPPSTORE_CONNECT_PRIVATE_KEY_P8=<paste p8 contents>",
                ),
            ],
            "instagram": [
                SetupStep(
                    title="Instagram Graph API",
                    detail="Use the Meta Business account linked to the #local Instagram business account.",
                ),
                SetupStep(
                    title="Generate a long-lived token",
                    detail="Meta Graph API Explorer → generate an access token with instagram_basic + insights.",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="INSTAGRAM_ACCESS_TOKEN=<token>",
                ),
            ],
            "linkedin": [
                SetupStep(
                    title="LinkedIn Marketing API",
                    detail="Create a LinkedIn Developer app with the 'Marketing Developer Platform' product.",
                ),
                SetupStep(
                    title="OAuth access token",
                    detail="Authorize the app and exchange for an access token with r_organization_social + rw_organization_admin.",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="LINKEDIN_ACCESS_TOKEN=<token>",
                ),
            ],
            "facebook": [
                SetupStep(
                    title="Meta Graph API",
                    detail="Use the Meta Business account for the #local Facebook page.",
                ),
                SetupStep(
                    title="Page access token",
                    detail="Graph API Explorer → generate a Page access token with pages_read_engagement.",
                ),
                SetupStep(
                    title="Add to .env",
                    detail="FACEBOOK_ACCESS_TOKEN=<token>",
                ),
            ],
        }
        return guides.get(source_id, [])

    def pull_all(self, entity: str) -> tuple[list[SourceRecord], bool]:
        """Return (records, any_source_configured). Phase 1 always uses the sample adapter."""
        configured = [c for c in self.real if c.is_configured()]
        if configured:
            records: list[SourceRecord] = []
            for c in configured:
                records.extend(c.pull())
            return records, True
        return self.sample.pull(), False
