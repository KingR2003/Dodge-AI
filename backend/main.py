from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers.chat_controller import router as chat_router
from controllers.graph_controller import router as graph_router


app = FastAPI(title="SAP O2C Graph Query API")

# Add CORS middleware to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_router)
app.include_router(chat_router)

