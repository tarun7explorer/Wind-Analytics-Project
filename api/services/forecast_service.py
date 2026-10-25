from api.services.elexon_client import ElexonClient
from api.utils.validation import unwrap_records


class ForecastService:
    """Fetch raw WINDFOR publication records, without latest-only fallback."""

    def __init__(self, client: ElexonClient):
        self.client = client

    async def get_publications(self, publish_from, publish_to) -> list[dict]:
        payload = await self.client.fetch_forecasts(publish_from, publish_to)
        return unwrap_records(payload, "WINDFOR")
