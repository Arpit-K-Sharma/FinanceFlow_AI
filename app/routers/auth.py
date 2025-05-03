from fastapi import APIRouter, Depends, Request, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import aiohttp
import os
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel

from app.models.models import UserAuth
from app.services.auth_service import AuthService, EndpointTestResult

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(tags=["Authentication"])
security = HTTPBearer()

# Get services dependency
def get_services():
    from app.main import app
    return app.state.services

# Get auth service helper
def get_auth_service():
    def dependency(services=Depends(get_services)):
        return services["auth_service"]
    return Depends(dependency)

# Get current user helper
def get_current_user_dependency():
    async def get_user(auth_service = get_auth_service()):
        return await auth_service.get_current_user()
    return Depends(get_user)

class TokenResponse(BaseModel):
    """Token validation response model"""
    user_id: str
    email: str
    is_valid: bool
    username: Optional[str] = None

class DebugResponse(BaseModel):
    """Debug endpoint response model"""
    status: str
    message: str
    backend_url: str
    tested_endpoints: List[EndpointTestResult]
    request_headers: Dict[str, str]

@router.get("/validate-token", response_model=TokenResponse)
async def validate_token(
    request: Request,
    auth_service: AuthService = get_auth_service()
) -> TokenResponse:
    """
    Validate an authentication token provided in the Authorization header
    
    Args:
        request: The FastAPI request
        auth_service: Injected authentication service
        
    Returns:
        TokenResponse: Information about the token validity and user
        
    Raises:
        HTTPException: If token validation fails
    """
    try:
        # Extract token from authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("No Authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="No token provided"
            )
        
        # Clean token format
        token = auth_header
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        
        # Log token validation attempt (first 8 chars only for security)
        token_preview = token[:8] + "..." if len(token) > 8 else token
        logger.info(f"Token validation request received: {token_preview}")
        
        # Validate token with service
        user = await auth_service.validate_token(token)
        
        # Return success response
        logger.info(f"Token validated successfully for user {user.id}")
        return TokenResponse(
            user_id=user.id,
            email=user.email,
            is_valid=True,
            username=user.username
        )
        
    except HTTPException as ex:
        # Re-raise HTTP exceptions
        logger.warning(f"Token validation failed with HTTP error: {ex.detail}")
        raise
        
    except Exception as ex:
        # Convert other exceptions to HTTP exceptions
        logger.error(f"Unexpected error during token validation: {str(ex)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token validation error: {str(ex)}"
        )

@router.get("/me", response_model=UserAuth)
async def get_current_user(
    auth_service: AuthService = get_auth_service(),
    user: UserAuth = Depends(lambda auth_service: auth_service.get_current_user)
) -> UserAuth:
    """
    Get the current authenticated user
    
    Args:
        auth_service: Injected authentication service
        user: The authenticated user (injected via dependency)
        
    Returns:
        UserAuth: The authenticated user
    """
    logger.info(f"User data requested for user ID: {user.id}")
    return user

@router.get("/test", response_model=List[EndpointTestResult])
async def test_token_validation(
    request: Request, 
    auth_service: AuthService = get_auth_service()
) -> List[EndpointTestResult]:
    """
    Test token validation with backend endpoints
    
    Args:
        request: The FastAPI request
        auth_service: Injected authentication service
        
    Returns:
        List[EndpointTestResult]: Results of endpoint tests
    """
    # Extract token from request if available
    auth_header = request.headers.get("Authorization")
    
    # Log test attempt
    logger.info(f"Token validation test requested, authorization header present: {auth_header is not None}")
    
    # Run endpoint tests
    results = await auth_service._test_endpoints(auth_header)
    
    # Log summary 
    success_count = sum(1 for r in results if r.status == "success")
    logger.info(f"Endpoint test completed: {success_count}/{len(results)} endpoints available")
    
    return results

@router.get("/debug", response_model=DebugResponse)
async def debug_endpoint(
    request: Request, 
    auth_service: AuthService = get_auth_service()
) -> DebugResponse:
    """
    Debug endpoint for authentication issues
    
    Args:
        request: The FastAPI request
        auth_service: Injected authentication service
        
    Returns:
        DebugResponse: Debugging information
    """
    # Extract request headers for debugging
    headers = {k: v for k, v in request.headers.items()}
    
    # Log debug request
    logger.info("Debug endpoint requested")
    
    # Test backends with the token if provided
    auth_header = headers.get("Authorization")
    endpoint_results = await auth_service._test_endpoints(auth_header)
    
    # Build debug response
    success_count = sum(1 for r in endpoint_results if r.status == "success")
    
    if success_count > 0:
        status = "healthy"
        message = f"Authentication service is working: {success_count}/{len(endpoint_results)} endpoints available"
    else:
        status = "error"
        message = "No backend endpoints are available. Authentication service cannot validate tokens."
    
    return DebugResponse(
        status=status,
        message=message,
        backend_url=auth_service.backend_url,
        tested_endpoints=endpoint_results,
        request_headers=headers
    ) 