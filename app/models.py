from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class DBAnomaly(Base):
    """Stores operational store anomalies."""
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    severity = Column(String)
    timestamp = Column(String)
    person_id = Column(Integer)
    duration_seconds = Column(Integer)
    details = Column(String)  # JSON serialized extra fields


class DBMetric(Base):
    """Stores key-value pair metrics from analytics.json."""
    __tablename__ = "metrics"
    
    key = Column(String, primary_key=True)
    value = Column(Float, nullable=False)


class DBOccupancy(Base):
    """Stores timeline points for occupancy levels over time."""
    __tablename__ = "occupancy_timeline"
    
    id = Column(Integer, primary_key=True, index=True)
    time = Column(String, nullable=False)
    occupancy = Column(Integer, nullable=False)


class DBVisitor(Base):
    """Stores statistics of store visitors."""
    __tablename__ = "visitors"
    
    person_id = Column(Integer, primary_key=True)
    track_duration = Column(Float, nullable=False)
    events_count = Column(Integer, default=0)
