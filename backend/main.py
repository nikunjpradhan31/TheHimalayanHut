from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from database import initialize_database, update_expired_keys
import uvicorn
from api import *
# API Imports
from api.users import router as user_router
from api.watchlist import router as watchlist_router
#from api.review import router as review_router
from api.movie import router as movie_router
from api.recommendations import router as recommendation_router
#from backend.tests.minio_function import router as minio_router
from api.cached_data import periodic_refresh

async def lifespan(app: FastAPI):
    print("Starting DB initialization")
    await initialize_database()
    print("DB initialized, starting background tasks")
    key_task = asyncio.create_task(update_expired_keys())
    cache_task = asyncio.create_task(periodic_refresh(10))

    print("Background tasks started")
    try:
        yield
    finally:
        print("Lifespan shutdown: cancelling background tasks")
        key_task.cancel()
        cache_task.cancel()
        await asyncio.gather(key_task, cache_task, return_exceptions=True)
        print("Background tasks cancelled")


# FastAPI app
app = FastAPI(lifespan=lifespan)
#router = APIRouter()
app.include_router(user_router,prefix="/api")
app.include_router(watchlist_router,prefix="/api")
#app.include_router(review_router,prefix="/himalayanhut")
app.include_router(movie_router,prefix="/api")
app.include_router(recommendation_router,prefix="/api")
#app.include_router(minio_router,prefix="/himalayanhut")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# CORS
origins = ["https://www.website.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7001, reload=False)
