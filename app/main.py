import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("DEBUG", "false").lower() != "true" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Wealth Management AI Service",
    description="AI Service for the Wealth Management Application",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize services
from app.services.auth_service import AuthService
from app.services.llm_service import LLMService
from app.services.data_aggregator import DataAggregatorService
from app.services.market_data import MarketDataService
from app.services.prompt_generator import PromptGeneratorService

# Get backend URL from environment
backend_url = os.getenv("BACKEND_URL")
if not backend_url:
    logger.warning("BACKEND_URL not set in environment. Using default: http://localhost:3000")
    backend_url = "http://localhost:3000"

# Ensure correct backend URL format (without /api suffix as that might be incorrect)
if backend_url.endswith('/api'):
    backend_url = backend_url[:-4]
    logger.info(f"Removed /api suffix from backend URL: {backend_url}")

# Get Google Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.error("GEMINI_API_KEY not set in environment. LLM functionality will be unavailable.")
    gemini_api_key = "missing_api_key"

# Get LLM model name from environment
llm_model = os.getenv("LLM_MODEL", "gemini-1.0-pro") # Default to gemini-1.0-pro if not specified

# Initialize API keys for market data
market_api_keys = {
    "alpha_vantage": os.getenv("ALPHA_VANTAGE_API_KEY", ""),
    "news_api": os.getenv("NEWS_API_KEY", "")
}

# Initialize services and store them in app.state
auth_service = AuthService(backend_url)
llm_service = LLMService(api_key=gemini_api_key, model=llm_model)
data_aggregator = DataAggregatorService(base_url=backend_url)
market_data = MarketDataService(api_keys=market_api_keys)
prompt_generator = PromptGeneratorService()

# Store services in app.state for access from routers
app.state.services = {
    "auth_service": auth_service,
    "llm_service": llm_service,
    "data_aggregator": data_aggregator,
    "market_data": market_data,
    "prompt_generator": prompt_generator
}

# Register exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc)
    error_type = type(exc).__name__
    error_trace = traceback.format_exc()
    
    # Log the error
    logger.error(f"Unhandled exception: {error_type} - {error_detail}")
    logger.debug(f"Error trace: {error_trace}")
    
    # Return a JSON response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": error_detail,
            "error_type": error_type
        }
    )

# Import routers
from app.routers import auth, financial

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(financial.router, prefix="/financial", tags=["Financial"])

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for the AI service
    """
    return {
        "status": "healthy",
        "service": "ai-service",
        "version": app.version,
        "backend_url": backend_url
    }

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint for the AI service
    """
    return {
        "service": "Wealth Management AI Service",
        "version": app.version,
        "docs_url": "/docs",
        "health_check": "/health"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting AI service on {host}:{port}")
    logger.info(f"Backend URL: {backend_url}")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)