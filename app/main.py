from fastapi import FastAPI


app = FastAPI(
    title="Autonomous Tender/RFP Intelligence & Bid/No-Bid Decision Engine",
    description=(
        "AI-powered system for analyzing tender and RFP documents, "
        "evaluating compliance, and generating explainable Bid/No-Bid decisions."
    ),
    version="0.1.0",
)


@app.get("/")
def root():
    """Return basic application information."""
    return {
        "project": "Autonomous Tender/RFP Intelligence & Bid/No-Bid Decision Engine",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    """Check whether the application is healthy."""
    return {
        "status": "healthy",
    }
