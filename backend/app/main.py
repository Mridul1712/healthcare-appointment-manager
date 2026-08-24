from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Base, engine
from app.routers.admin import router as admin_router
from app.routers.appointments import router as appointments_router
from app.routers.auth import router as auth_router
from app.routers.doctors import router as doctors_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(_, exc):
    return JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api")
def api_root():
    return {"message": settings.app_name, "endpoints": ["/api/auth/login", "/api/auth/register", "/api/doctors", "/api/appointments"]}


Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(admin_router)
