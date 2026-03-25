"""
Infinity Governance API - Main Application Entry Point
Structured with separated concerns: models, config, utils, and API routers
"""
from app import app

if __name__ == "__main__":
    import uvicorn
    from app.config import SERVER_HOST, SERVER_PORT
    
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
