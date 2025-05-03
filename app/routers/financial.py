from fastapi import APIRouter, Depends, HTTPException, Request
import logging

from app.models.models import (
    FinancialAdvice, 
    ChatHistory, 
    UserAuth, 
    AdviceRequest, 
    ChatRequest, 
    ChatResponse
)
from app.services.auth_service import AuthService, oauth2_scheme
from app.services.data_aggregator import DataAggregatorService
from app.services.market_data import MarketDataService
from app.services.llm_service import LLMService
from app.services.prompt_generator import PromptGeneratorService

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(tags=["financial"])

# Get services dependency
def get_services():
    from app.main import app
    return app.state.services

# Get current user helper
def get_current_user_dependency():
    def dependency(services=Depends(get_services), request: Request = None):
        auth_service = services["auth_service"]
        return auth_service.get_current_user(request)
    return Depends(dependency)

@router.post("/advice", response_model=FinancialAdvice)
async def generate_advice(
    request: Request,
    request_data: AdviceRequest,
    token: str = Depends(oauth2_scheme),
    services = Depends(get_services)
):
    """
    Generate personalized financial advice for the authenticated user
    
    This endpoint combines the user's actual financial data (retrieved automatically from the backend)
    with their specific question or concern (if provided in the message field) to generate tailored
    financial advice.
    
    The response includes:
    - Insights based on spending patterns and financial status
    - Specific recommendations for savings, expenses, and investments
    - Relevant market context
    - Summary of overall financial health
    
    If a message is provided, the advice will explicitly address that specific question or concern
    while still providing comprehensive analysis based on the user's financial data.
    """
    try:
        # Get auth service and validate user first
        auth_service = services["auth_service"]
        current_user = await auth_service.get_current_user(request)
        
        # Get necessary services
        data_aggregator: DataAggregatorService = services["data_aggregator"]
        market_data: MarketDataService = services["market_data"]
        prompt_generator: PromptGeneratorService = services["prompt_generator"]
        llm_service: LLMService = services["llm_service"]
        
        # Get user data using the authenticated user's ID and the provided token
        # We use the same token that's used for frontend->backend authentication
        user_data = await data_aggregator.get_user_financial_data(
            user_id=current_user.id,
            user_token=token
        )
        
        # Get market data
        market_summary = await market_data.get_market_summary()
        
        # Generate prompt
        prompt = prompt_generator.generate_financial_advice_prompt(
            user_data=user_data,
            market_data=market_summary,
            user_message=request_data.message
        )
        
        # Generate advice
        advice = await llm_service.generate_financial_advice(prompt)
        
        return advice
    except Exception as e:
        logger.error(f"Error generating advice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating advice: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def generate_chat_response(
    request: Request,
    request_data: ChatRequest,
    token: str = Depends(oauth2_scheme),
    services = Depends(get_services)
):
    """
    Generate chat response for the authenticated user
    """
    try:
        # Get auth service and validate user first
        auth_service = services["auth_service"]
        current_user = await auth_service.get_current_user(request)
        
        # Get necessary services
        data_aggregator: DataAggregatorService = services["data_aggregator"]
        market_data: MarketDataService = services["market_data"]
        prompt_generator: PromptGeneratorService = services["prompt_generator"]
        llm_service: LLMService = services["llm_service"]
        
        # Get user data using the authenticated user's ID and the provided token
        user_data = await data_aggregator.get_user_financial_data(
            user_id=current_user.id,
            user_token=token
        )
        
        # Get market data
        market_summary = await market_data.get_market_summary()
        
        # Generate prompt
        prompt = prompt_generator.generate_chat_prompt(
            user_data=user_data,
            market_data=market_summary,
            user_message=request_data.content,
            chat_history=request_data.chat_history
        )
        
        # Generate response
        response = await llm_service.generate_chat_response(prompt)
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating chat response: {str(e)}")

@router.get("/health")
async def health_check(services = Depends(get_services)):
    """
    Check the health of the financial services
    """
    try:
        return {
            "status": "healthy",
            "message": "Financial AI service is running",
            "services": {
                "llm": services["llm_service"] is not None,
                "market_data": services["market_data"] is not None,
                "prompt_generator": services["prompt_generator"] is not None,
                "data_aggregator": services["data_aggregator"] is not None
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service health check failed: {str(e)}")

@router.get("/api-key-check")
async def check_api_key(services = Depends(get_services)):
    """
    Check if the Gemini API key is properly configured
    """
    try:
        llm_service = services["llm_service"]
        api_key = llm_service.genai.api_key
        
        # Check if API key is set
        if not api_key:
            return {
                "status": "error",
                "message": "Gemini API key is not set. Please check your .env file."
            }
        
        # Check first few characters (safe to display)
        key_preview = api_key[:4] + "..." if len(api_key) > 4 else "too_short"
        
        return {
            "status": "ok",
            "message": f"Gemini API key is set (starts with {key_preview})",
            "model": llm_service.model
        }
    except Exception as e:
        logger.error(f"Error checking API key: {str(e)}")
        return {
            "status": "error",
            "message": f"Error checking API key: {str(e)}"
        } 