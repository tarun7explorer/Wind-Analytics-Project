from api.services.elexon_client import ElexonClient
from api.utils.validation import SourceDataError, unwrap_records


class ActualsService:
    """Normalize FUELHH rows and enforce the WIND category locally."""

    def __init__(self, client: ElexonClient):
        self.client = client

    async def get_month(self, year: int, month: int) -> list[dict]:
        payload = await self.client.fetch_actuals(year, month)
        records = unwrap_records(payload, "FUELHH")
        # Apply the wind constraint locally too, so a provider that ignores the
        # query filter cannot contaminate the report.
        wind = [row for row in records if str(row.get("fuelType", "")).upper() == "WIND"]
        if records and not wind:
            raise SourceDataError("FUELHH response contains no WIND records")
        return wind
