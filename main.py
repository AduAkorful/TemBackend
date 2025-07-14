from fastapi import FastAPI
from upload_routes import router as upload_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend on localhost:8080 and Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://smart-test-hub.vercel.app",
        "https://smarttesthub-backend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)

@app.get("/")
def read_root():
    return {"message": "Smart Contract Testing API is running"}

# For local dev
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
