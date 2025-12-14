from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.auth import login, set_password, user_creation, users_management
from app.auth.dependencies import require_roles
from app.api_kpi.kpi_router import router as kpi_router
from app.raw_activityapi.raw_routes import router as raw_activity_router
from app.raw_activityapi.requests_routes import router as requests_router
from app.raw_activityapi.admin_requests_routes import router as admin_router
from app.api_kpibatch.kpibatch_router import router as productivity_router
from rag_pipeline.retreiver import retrieve_and_answer
from app.assiatntapi.assistant_router import router as assistant_router
from app.report.classifications_routers import router as classifications_router
from app.report.summaries_router import router as summaries_router
from app.api_taskMatcher.taskMatcher_router import router as taskmatcher_router
from app.api_taskMatcher.taskPrediction_router import router as taskprediction_router

app = FastAPI()

# Allow frontend (React) to call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://193.95.30.190:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Public endpoints (accessible by all authenticated users)
# -----------------------------
app.include_router(login.router, prefix="/api")
app.include_router(set_password.router, prefix="/api")

# -----------------------------
# User-accessible endpoints
# -----------------------------
user_routes = [
    (kpi_router, "/kpi"),
    (raw_activity_router, "/raw_activity"),
    (productivity_router, "/api"),
    (assistant_router, "/ai"),
    (requests_router, "/requests"),
    (classifications_router, "/report"),
    (summaries_router, "/report"),
]

for router, prefix in user_routes:
    app.include_router(router, prefix=prefix, dependencies=[Depends(require_roles(["user", "admin"]))])

# -----------------------------
# Admin-only endpoints
# -----------------------------
admin_routes = [
    (users_management.router, "/api"),
    (user_creation.router, "/api"),
    (admin_router, "/admin"),
    (taskmatcher_router, "/taskmatcher"),
    (taskprediction_router, "/taskprediction")
]

for router, prefix in admin_routes:
    app.include_router(router, prefix=prefix, dependencies=[Depends(require_roles(["admin"]))])
