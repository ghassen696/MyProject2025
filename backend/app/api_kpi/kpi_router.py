from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
from app.api_kpi.kpi_services import get_today_kpi

router = APIRouter()

from pydantic import BaseModel
from typing import List, Optional

class Event(BaseModel):
    event: str
    timestamp: int 

class EmployeeKPI(BaseModel):
    employee_id: str
    date: int  # timestamp (ms)
    first_event_time: Optional[int] = None
    last_event_time: int
    total_idle_today: float
    pauses_today: int
    total_pause_minutes_today: float
    keystrokes_today: int
    last_idle_duration: Optional[float] = None
    events_today: List[Event]
    employee_status: str
    doc_id: str
    keystrokes_per_minute: Optional[float] = None
    active_minutes: Optional[float] = None




@router.get("/", response_model=List[EmployeeKPI])
async def fetch_today_kpi(
    employee_id: Optional[str] = Query(None, description="Filter by employee_id"),
    status: Optional[str] = Query(None, description="Filter by employee_status"),
    size: int = Query(50, description="Number of results to return"),
    #added for testing with old date 
    #date: Optional[int] = Query(None, description="Timestamp in ms to fetch specific date"),

):
    """
    Get today's KPI data:
    - If employee_id is given → only that employee
    - If no employee_id → all employees
    - Optional filter by status
    """
    #data = await get_today_kpi(employee_id, status, size, date)
    data = await get_today_kpi(employee_id, status, size)

    if not data:
        raise HTTPException(status_code=404, detail="No KPI data found for today")
    return data

