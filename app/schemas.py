from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

#Camera Node Schemas

class CameraNodeCreate(BaseModel):
    location_name: str = Field(..., example="International Departure Gate 3")
    status: Optional[str] = "active"

class CameraNode(BaseModel):
    node_id: int
    location_name: str
    status: str

    class Config:
        from_attributes = True

#Queue Metrics Schemas

class QueueMetricCreate(BaseModel):
    node_id: int
    current_headcount: int
    flow_rate_per_min: float
    estimated_wait_time_mins: float

class QueueMetric(BaseModel):
    metric_id: int
    timestamp: datetime
    node_id: int
    current_headcount: int
    flow_rate_per_min: float
    estimated_wait_time_mins: float

    class Config:
        from_attributes = True