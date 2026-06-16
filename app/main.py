from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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
    db.commit()
    db.refresh(new_metric)
    return new_metric