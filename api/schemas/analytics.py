from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MetricsResponse(BaseModel):
    matched_intervals: int
    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    wape_percent: Optional[float]


class HourlyAnalysisResponse(BaseModel):
    comparison_frequency: str
    actual_method: str
    expected_periods: int
    eligible_actual_periods: int
    actual_incomplete_periods: int
    forecast_periods: int
    matched_periods: int
    unmatched_periods: int
    actual_completeness_percent: Optional[float]
    forecast_coverage_percent: Optional[float]
    exact_half_hour_matched_periods: int
    exact_half_hour_expected_periods: int
    exact_half_hour_coverage_percent: Optional[float]
    metrics: MetricsResponse


class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    period_start: datetime
    period_end_exclusive: datetime
    timezone: str
    unit: str
    source_retrieved_at: datetime
    source_contract_status: str
    decision_cutoff_rule: str
    expected_intervals: int
    actual_intervals: int
    forecast_intervals: int
    matched_intervals: int
    unmatched_intervals: int
    missing_actual_intervals: int
    missing_forecast_intervals: int
    metrics: MetricsResponse
    hourly_analysis: HourlyAnalysisResponse


class AnalyticsRecordResponse(BaseModel):
    delivery_time: datetime
    forecast_mw: Optional[float]
    actual_mw: Optional[float]
    signed_error_mw: Optional[float]
    absolute_error_mw: Optional[float]
    percentage_error: Optional[float]
    forecast_published_at: Optional[datetime]
    decision_cutoff: datetime
    matched: bool


class HourlyAnalyticsRecordResponse(AnalyticsRecordResponse):
    actual_half_hour_count: int


class FullAnalyticsReportResponse(MonthlySummaryResponse):
    records: list[AnalyticsRecordResponse]
    hourly_records: list[HourlyAnalyticsRecordResponse]


class RecordsResponse(BaseModel):
    year: int
    month: int
    total: int
    offset: int
    limit: int
    records: list[AnalyticsRecordResponse]
