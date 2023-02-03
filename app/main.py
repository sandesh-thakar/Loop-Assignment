from fastapi import FastAPI

from .api import router

app = FastAPI(
    title="Loop Project",
    version="1.0",
    contact={
        "name": "Sandesh Thakar",
        "email": "sandesh.thakar18@gmail.com",
    },
    docs_url="/loop/docs",
    redoc_url="/loop/redoc",
    openapi_url="/loop/openapi.json",
)

app.include_router(router)
