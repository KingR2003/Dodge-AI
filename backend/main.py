import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the root .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers.chat_controller import router as chat_router
from controllers.graph_controller import router as graph_router

# Setup basic logging to see boot messages in Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Booting SAP O2C API. CWD: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")

app = FastAPI(title="SAP O2C Graph Query API")

# Add CORS middleware to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "cwd": os.getcwd(),
        "python_version": sys.version,
        "gemini_enabled": bool(os.environ.get("GEMINI_API_KEY"))
    }

app.include_router(graph_router)
app.include_router(chat_router)

