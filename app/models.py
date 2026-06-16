from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class CameraNode(Base):
    __tablename__ = "camera_nodes"

    node_id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")

class QueueMetric(Base):
    __tablename__ = "queue_metrics"

    metric_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    node_id = Column(Integer, ForeignKey("camera_nodes.node_id"), nullable=False)
    current_headcount = Column(Integer, nullable=False)
    flow_rate_per_min = Column(Float, nullable=False)
    estimated_wait_time_mins = Column(Float, nullable=False)

class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    node_id = Column(Integer, ForeignKey("camera_nodes.node_id"), nullable=False)
    alert_type = Column(String, nullable=False)
    resolved_status = Column(Boolean, default=False)