from fastapi import FastAPI

from app.routers import reference
from app.routers import reference, avis

from app.routers import reference, avis, imports
from app.routers import reference, avis, imports, dashboard


app = FastAPI(
    title="Bakeli Insights API",
    description="Backend de la plateforme d'écoute et d'analyse de sentiments Bakeli.",
    version="0.1.0",
)

app.include_router(reference.router)
app.include_router(avis.router)
app.include_router(imports.router)
app.include_router(dashboard.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}