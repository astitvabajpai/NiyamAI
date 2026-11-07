"""Entry point for NiyamAI FastAPI server."""

import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("src.api:app", host=host, port=port, reload=True)
