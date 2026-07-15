from analytics_agent.config.settings import Settings
from analytics_agent.domain.models import SourceRecord
from analytics_agent.tools.connectors.base import BaseConnector


class GA4Connector(BaseConnector):
    """Google Analytics 4 — website + app streams. Live in Phase 2."""

    id = "ga4"
    name = "Google Analytics 4"
    env_var = "GA4_PROPERTY_ID + GA4_CREDENTIALS_JSON"

    def is_configured(self) -> bool:
        return bool(self.settings.ga4_property_id and self.settings.ga4_credentials_json)

    def pull(self) -> list[SourceRecord]:
        # Phase 1: connector exists but is inert until keys are set.
        return []


class BusinessDbConnector(BaseConnector):
    """Business DB — signups, orders, revenue. Live in Phase 2."""

    id = "business_db"
    name = "Business DB"
    env_var = "BUSINESS_DB_URL"

    def is_configured(self) -> bool:
        return bool(self.settings.business_db_url)

    def pull(self) -> list[SourceRecord]:
        return []


class PlayStoreConnector(BaseConnector):
    """Google Play — installs, ratings. Live in Phase 2."""

    id = "play_store"
    name = "Google Play"
    env_var = "PLAY_STORE_CREDENTIALS_JSON"

    def is_configured(self) -> bool:
        return bool(self.settings.play_store_credentials_json)

    def pull(self) -> list[SourceRecord]:
        return []


class AppStoreConnector(BaseConnector):
    """Apple App Store Connect — installs, ratings. Live in Phase 2."""

    id = "app_store"
    name = "Apple App Store"
    env_var = "APPSTORE_CONNECT_KEY_ID + APPSTORE_CONNECT_ISSUER_ID + APPSTORE_CONNECT_PRIVATE_KEY_P8"

    def is_configured(self) -> bool:
        return bool(
            self.settings.appstore_connect_key_id
            and self.settings.appstore_connect_issuer_id
            and self.settings.appstore_connect_private_key_p8
        )

    def pull(self) -> list[SourceRecord]:
        return []


class InstagramConnector(BaseConnector):
    """Instagram — reach, engagement, follower growth. Live in Phase 2."""

    id = "instagram"
    name = "Instagram"
    env_var = "INSTAGRAM_ACCESS_TOKEN"

    def is_configured(self) -> bool:
        return bool(self.settings.instagram_access_token)

    def pull(self) -> list[SourceRecord]:
        return []


class LinkedInConnector(BaseConnector):
    """LinkedIn — reach, engagement. Live in Phase 2."""

    id = "linkedin"
    name = "LinkedIn"
    env_var = "LINKEDIN_ACCESS_TOKEN"

    def is_configured(self) -> bool:
        return bool(self.settings.linkedin_access_token)

    def pull(self) -> list[SourceRecord]:
        return []


class FacebookConnector(BaseConnector):
    """Facebook — reach, engagement. Live in Phase 2."""

    id = "facebook"
    name = "Facebook"
    env_var = "FACEBOOK_ACCESS_TOKEN"

    def is_configured(self) -> bool:
        return bool(self.settings.facebook_access_token)

    def pull(self) -> list[SourceRecord]:
        return []


def build_connectors(settings: Settings | None = None) -> list[BaseConnector]:
    return [
        GA4Connector(settings),
        BusinessDbConnector(settings),
        PlayStoreConnector(settings),
        AppStoreConnector(settings),
        InstagramConnector(settings),
        LinkedInConnector(settings),
        FacebookConnector(settings),
    ]
