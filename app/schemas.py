"""
Pydantic Schemas for Request/Response Validation and Serialization.
Uses Pydantic V2 style structures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Pydantic schema for endpoint GET /health."""
    status: str = Field(..., examples=["healthy"])
    version: str = Field(..., examples=["1.0"])


class MetricsResponse(BaseModel):
    """Pydantic schema for endpoint GET /metrics."""
    total_entries: int = Field(..., examples=[120])
    total_exits: int = Field(..., examples=[117])
    unique_visitors: int = Field(..., examples=[98])
    peak_occupancy: int = Field(..., examples=[21])
    avg_visit_duration: float = Field(..., examples=[245.3])


class FunnelResponse(BaseModel):
    """Pydantic schema for endpoint GET /funnel."""
    total_passersby: int = Field(..., examples=[150])
    entered_store: int = Field(..., examples=[98])
    browsed_aisle: int = Field(..., examples=[45])
    checkout: int = Field(..., examples=[12])
    conversion_rates: Dict[str, float] = Field(
        ...,
        examples=[{
            "entry_rate": 0.653,
            "browse_rate": 0.459,
            "purchase_rate": 0.267
        }]
    )


class AnomalyItem(BaseModel):
    """Pydantic schema representing a single anomaly entry."""
    id: Optional[int] = Field(None, examples=[1])
    type: str = Field(..., examples=["loitering"])
    severity: Optional[str] = Field(None, examples=["high"])
    timestamp: Optional[str] = Field(None, examples=["2026-04-10T12:15:22"])
    person_id: Optional[int] = Field(None, examples=[15])
    duration_seconds: Optional[int] = Field(None, examples=[1250])
    details: Optional[Dict[str, Any]] = Field(None, examples=[{"peak_occupancy": 3}])

    model_config = ConfigDict(from_attributes=True)


class AnomalySummary(BaseModel):
    """Pydantic schema representing the aggregated anomaly counts."""
    total_anomalies: int = Field(..., examples=[10])
    crowding: int = Field(..., examples=[4])
    loitering: int = Field(..., examples=[3])
    traffic_spikes: int = Field(..., examples=[3])


class AnomaliesResponse(BaseModel):
    """Pydantic schema for endpoint GET /anomalies."""
    summary: AnomalySummary
    anomalies: List[AnomalyItem]


class OccupancyItem(BaseModel):
    """Pydantic schema representing a single occupancy log entry."""
    time: str = Field(..., examples=["12:10:34"])
    occupancy: int = Field(..., examples=[1])


class OccupancyResponse(BaseModel):
    """Pydantic schema for endpoint GET /occupancy."""
    timeline: List[OccupancyItem]


class VisitorItem(BaseModel):
    """Pydantic schema representing a single visitor detail log."""
    person_id: int = Field(..., examples=[10])
    track_duration: float = Field(..., examples=[3.5])
    events_count: int = Field(..., examples=[2])


class VisitorAnalyticsResponse(BaseModel):
    """Pydantic schema for endpoint GET /visitors."""
    total_visitors: int = Field(..., examples=[28])
    avg_duration: float = Field(..., examples=[12.1])
    longest_duration: float = Field(..., examples=[93.7])
    visitors: List[VisitorItem]
