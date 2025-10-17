print(">>> Importing upload from:", __file__)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import upload, query

print(">>> upload module path:", upload.__file__)
print(">>> upload dir contents:", dir(upload))

app = FastAPI(title="Personal RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "RAG Backend is running!"}


# from fastapi import FastAPI

# app = FastAPI()

# @app.get("/")
# def hello():
#     return {"message": "Hello from minimal app!"}