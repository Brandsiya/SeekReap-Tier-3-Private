from fastapi import FastAPI

app = FastAPI()

# Root route to test server
@app.get("/")
async def root():
    return {"status": "SeekReap Tier-3 is running!"}

# Example orchestrator route
@app.get("/orchestrate")
async def orchestrate():
    return {"message": "Orchestration endpoint working!"}

# Add this if using python3 main.py locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
