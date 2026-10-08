from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.save_metrics import get_metrics, init_db
from ingestion.ingest_documents import get_vector_store
from routes.chat import router as chat_router
from routes.ingestion import router as ingestion_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: make sure the DB table and the OpenSearch index exist."""
    init_db()
    try:
        get_vector_store()   # creates the index if missing
    except Exception as e:
        print(f"Warning: could not initialise OpenSearch index: {e}")
    yield


app = FastAPI(title="AI-Powered Investor Intelligence Platform", lifespan=lifespan)

app.include_router(ingestion_router, prefix="/api", tags=["Ingestion"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def dashboard(request: Request):
    metrics = get_metrics()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "metrics": metrics,
            "total_companies": len({m["company"] for m in metrics}),
            "total_reports": len(metrics),
        },
    )


@app.get("/api/metrics")
def metrics():
    return JSONResponse(content=get_metrics())


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)