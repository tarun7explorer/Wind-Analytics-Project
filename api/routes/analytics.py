from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.schemas.analytics import FullAnalyticsReportResponse, MonthlySummaryResponse, RecordsResponse
from api.services.actuals_service import ActualsService
from api.services.elexon_client import ElexonClient, ElexonUnavailableError
from api.services.forecast_service import ForecastService
from api.services.monthly_report_service import MonthlyReportService
from api.utils.validation import SourceDataError

def disable_response_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(disable_response_caching)])


def get_report_service() -> MonthlyReportService:
    client = ElexonClient()
    return MonthlyReportService(ActualsService(client), ForecastService(client))


async def _load_report(year: int, month: int, service: MonthlyReportService) -> dict:
    try:
        return await service.get_report(year, month)
    except ElexonUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SourceDataError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid Elexon response: {exc}") from exc


@router.get("/monthly", response_model=MonthlySummaryResponse)
async def monthly_analytics(
    year: int = Query(default=2026, ge=1, le=9998),
    month: int = Query(default=1, ge=1, le=12),
    service: MonthlyReportService = Depends(get_report_service),
) -> dict:
    report = await _load_report(year, month, service)
    return {k: v for k, v in report.items() if k != "records"}


@router.get("/report", response_model=FullAnalyticsReportResponse)
async def full_analytics_report(
    year: int = Query(default=2026, ge=1, le=9998),
    month: int = Query(default=1, ge=1, le=12),
    service: MonthlyReportService = Depends(get_report_service),
) -> dict:
    """Return source intervals and hourly comparison from one upstream snapshot."""
    return await _load_report(year, month, service)


@router.get("/records", response_model=RecordsResponse)
async def detailed_records(
    year: int = Query(default=2026, ge=1, le=9998),
    month: int = Query(default=1, ge=1, le=12),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    service: MonthlyReportService = Depends(get_report_service),
) -> dict:
    report = await _load_report(year, month, service)
    records = report["records"]
    return {
        "year": year,
        "month": month,
        "total": len(records),
        "offset": offset,
        "limit": limit,
        "records": records[offset:offset + limit],
    }
