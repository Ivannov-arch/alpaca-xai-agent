"""
main.py — Convenience entry point to run the XAI Trading Agent FastAPI server.
"""
import uvicorn
from agent.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("agent.api.main:app", host=API_HOST, port=API_PORT, reload=True)
