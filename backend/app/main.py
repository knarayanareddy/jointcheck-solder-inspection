from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title="JointCheck — Solder Joint Workmanship Inspection with Proof",
    description="Macro-photo electronics joint inspection grading against workmanship criteria — OpenCV geometric feature extraction, Nemotron Ultra reasoning across Class 1/2/3, tri-state deterministic gating with formal abstention, and Sandbox A/B branch verification.",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}

@app.get("/v1/info")
def get_info():
    return {
        "project": "JointCheck — Solder Joint Workmanship Inspection with Proof",
        "track": "Best Apps and Agents (or Physical AI)",
        "models": {
            "ultra": settings.model_ultra,
            "super": settings.model_super,
            "nano": settings.model_nano
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
