from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
import json

from app.database import engine, Base, SessionLocal
import app.models as models
import app.schemas as schemas


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AeroFlow AI API",
    description="Backend engine for real-time airport queue density and wait-time estimation",
    version="1.0.0"
)

#Database Dependancy, opening session per request and closing it
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#Websock connection manager
class ConnectionManager:
    def __init__(self):
        #keep track of active websocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


#Camera node endpoints
@app.post("/api/v1/cameras", response_model=schemas.CameraNode, status_code=status.HTTP_201_CREATED)
def create_camera_node(camera: schemas.CameraNodeCreate, db: Session = Depends(get_db)):
    #checking if a camera with this location name already exists
    db_camera = db.query(models.CameraNode).filter(models.CameraNode.location_name == camera.location_name).first()
    if db_camera:
        raise HTTPException(status_code=400, detail="Camera location already registered")
    
    #new database entry
    new_node = models.CameraNode(location_name=camera.location_name, status=camera.status)
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node

@app.get("/api/v1/cameras", response_model=List[schemas.CameraNode])
def get_all_cameras(db: Session = Depends(get_db)):
    return db.query(models.CameraNode).all()


#Queue Metrics endpoints
@app.post("/api/v1/metrics", response_model=schemas.QueueMetric, status_code=status.HTTP_201_CREATED)
def receive_queue_metrics(metric: schemas.QueueMetricCreate, db: Session = Depends(get_db)):
    #verify target camera node exists
    camera_exists = db.query(models.CameraNode).filter(models.CameraNode.node_id == metric.node_id).first()
    if not camera_exists:
        raise HTTPException(status_code=404, detail=f"Camera node with ID {metric.node_id} not found")
    
    #create the new metrics entry
    new_metric = models.QueueMetric(
        node_id=metric.node_id,
        current_headcount=metric.current_headcount,
        flow_rate_per_min=metric.flow_rate_per_min,
        estimated_wait_time_mins=metric.estimated_wait_time_mins
    )
    db.add(new_metric)
    
    #Intelligent alerting, if wait time is greater than 15mins generate alert
    if metric.estimated_wait_time_mins > 15.0:
        #check if an unresolved alert already exists for this node to prevent flooding the DB
        existing_alert = db.query(models.Alert).filter(
            models.Alert.node_id == metric.node_id,
            models.Alert.resolved_status == False
        ).first()

        if not existing_alert:
            new_alert = models.Alert(
                node_id=metric.node_id,
                alert_type="Critical Congestion"
            )
            db.add(new_alert)

        db.commit()
        db.refresh(new_metric)
        return new_metric

#fetches the single absolute latest metric entry for every camera node
@app.get("/api/v1/queues/current", response_model=List[schemas.QueueMetric])
def get_current_queues(db: Session = Depends(get_db)):
    cameras = db.query(models.CameraNode).all()
    latest_metrics = []

    for camera in cameras:
        metric = db.query(models.QueueMetric)\
            .filter(models.QueueMetric.node_id == camera.node_id)\
            .order_by(models.QueueMetric.timestamp.desc())\
            .first()
        if metric:
            latest_metrics.append(metric)
    return latest_metrics


#Alert endpoints
@app.get("/api/v1/alerts", response_model=List[schemas.AlertOut])
def get_active_alerts(db: Session = Depends(get_db)):
    return db.query(models.Alert).filter(models.Alert.resolved_status == False).all()

#the actual tunnel route the frontend dashboard will connect to
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            #keep connection alive by waiting for any incoming ping text
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)