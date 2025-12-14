from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
from app.api_kpi.kpi_services import get_today_kpi
import json

router = APIRouter()

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

class Event(BaseModel):
    event: str
    timestamp: datetime 

class EmployeeKPI(BaseModel):
    employee_id: str
    date: date
    first_event_time: datetime = None
    last_event_time: datetime = None
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
):
    """
    Get today's KPI data:
    - If employee_id is given → only that employee
    - If no employee_id → all employees
    - Optional filter by status
    """
    data = await get_today_kpi(employee_id, status, size)

    if not data:
        raise HTTPException(status_code=404, detail="No KPI data found for today")
    
    # Transform the data: parse events_today_json into events_today
    for item in data:
        if 'events_today_json' in item:
            try:
                # Parse the JSON string into a list of dicts
                item['events_today'] = json.loads(item['events_today_json'])
                # Remove the old field to avoid confusion
                del item['events_today_json']
            except json.JSONDecodeError:
                # If parsing fails, set to empty list
                item['events_today'] = []
        elif 'events_today' not in item:
            # If neither field exists, set to empty list
            item['events_today'] = []
    
    return data