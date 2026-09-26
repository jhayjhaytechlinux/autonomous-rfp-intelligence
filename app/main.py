from fastapi import FastAPI

from app.api.routes_analysis import router as analysis_router
from app.api.routes_rfp import router as rfp_router


app = FastAPI(
    title="Autonomous RFP Intelligence Engine",
    description=(
        "AI-powered RFP analysis and bid/no-bid "
        "decision support system."
    ),
    version="0.1.0",
)


app.include_router(rfp_router)
app.include_router(analysis_router)


@app.get("/")
def root():
    """Return basic application information."""

    return {
        "name": "Autonomous RFP Intelligence Engine",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    """Return application health status."""

    return {
        "status": "healthy",
    }
