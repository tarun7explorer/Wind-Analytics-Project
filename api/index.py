from fastapi import FastAPI

from api.routes.analytics import router as analytics_router
from api.routes.health import router as health_router

app = FastAPI(
    title="Wind Forecast Analytics API",
    version="0.1.0",
    description="UK national wind generation forecast accuracy based on Elexon FUELHH and WINDFOR.",
)
app.include_router(health_router)
app.include_router(analytics_router)

# Vercel promotes the Vite output to its CDN. API routes above retain priority;
# extensionless frontend paths use index.html for client-side SPA navigation.
app.frontend("/", directory="dist", fallback="index.html", check_dir=False)
