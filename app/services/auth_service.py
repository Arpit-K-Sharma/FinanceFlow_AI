import os
import logging
import time
import json
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, Request, status
from pydantic import BaseModel
from urllib.parse import urljoin
from fastapi.security import OAuth2PasswordBearer

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserAuth(BaseModel):
    """User authentication data model"""
    id: str
    email: str
    username: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: str

class EndpointTestResult(BaseModel):
    """Endpoint test result model"""
    endpoint: str
    status: str
    message: str
    response_code: Optional[int] = None
    response_text: Optional[str] = None

class AuthService:
    """Authentication service for user authentication and token validation"""
    
    def __init__(self, backend_url: str, timeout: int = 10):
        """
        Initialize the AuthService
        
        Args:
            backend_url: The URL of the backend service
            timeout: Request timeout in seconds
        """
        self.backend_url = backend_url
        self.timeout = timeout
        
        # Define validation endpoints
        self.validate_endpoints = [
            urljoin(backend_url, "/api/users/profile"),  # Main profile endpoint
            urljoin(backend_url, "/api/test")           # Test endpoint to check connectivity
        ]
        
        # Define health check endpoints
        self.health_endpoints = [
            urljoin(backend_url, "/api/test"),
            urljoin(backend_url, "/api/health")
        ]
        
        logger.info(f"AuthService initialized with backend URL: {backend_url}")
        logger.debug(f"Validation endpoints: {self.validate_endpoints}")
        logger.debug(f"Health check endpoints: {self.health_endpoints}")

    async def validate_token(self, token: str) -> UserAuth:
        """
        Validate an authentication token
        
        Args:
            token: The token to validate
            
        Returns:
            UserAuth: The authenticated user information
            
        Raises:
            HTTPException: If the token is invalid or validation fails
        """
        if not token:
            logger.warning("No token provided for validation")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided"
            )
        
        logger.debug(f"Validating token (first 10 chars): {token[:10]}...")
        
        # Try multiple endpoints for validation
        exceptions = []
        
        # Standard headers
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in self.validate_endpoints:
                try:
                    logger.debug(f"Trying validation endpoint: {endpoint}")
                    response = await client.get(endpoint, headers=headers)
                    
                    # Log response status
                    logger.debug(f"Response status: {response.status_code}")
                    
                    # If successful, parse user data
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.debug(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            
                            # Handle different response formats
                            user_data = None
                            if isinstance(data, dict):
                                if "user" in data:
                                    user_data = data["user"]
                                elif "data" in data and isinstance(data["data"], dict):
                                    user_data = data["data"]
                                    # If the first endpoint (profile) is hit, it's a proper user profile
                                    if endpoint == self.validate_endpoints[0]:
                                        # Map to expected fields
                                        return UserAuth(
                                            id=str(user_data.get("id")),
                                            email=user_data.get("email", ""),
                                            username=user_data.get("name", ""),
                                            role=user_data.get("role", "user")
                                        )
                                elif "status" in data and data["status"] == "success" and "data" in data:
                                    # Backend success response format
                                    user_data = data["data"]
                                    # Check if this is a minimal response from the test endpoint
                                    if endpoint == self.validate_endpoints[1] and "message" in user_data:
                                        # This is just a connectivity test, create minimal user
                                        return UserAuth(
                                            id="system",
                                            email="system@example.com",
                                            role="system"
                                        )
                                else:
                                    # Assume the response is the user data itself
                                    user_data = data
                            
                            if user_data:
                                logger.info(f"Token validated successfully with endpoint: {endpoint}")
                                return UserAuth(**user_data)
                            else:
                                logger.warning(f"Response successful but no user data found with endpoint: {endpoint}")
                                exceptions.append(f"No user data in response from {endpoint}")
                        except Exception as ex:
                            logger.error(f"Error parsing response from {endpoint}: {str(ex)}")
                            exceptions.append(f"Error parsing response from {endpoint}: {str(ex)}")
                    else:
                        # Log the error response
                        try:
                            error_data = response.json()
                            logger.warning(f"Validation failed with endpoint {endpoint}: {error_data}")
                            exceptions.append(f"Validation failed with endpoint {endpoint}: {error_data}")
                        except:
                            logger.warning(f"Validation failed with endpoint {endpoint}: {response.text}")
                            exceptions.append(f"Validation failed with endpoint {endpoint}: {response.text}")
                except Exception as ex:
                    logger.error(f"Error connecting to endpoint {endpoint}: {str(ex)}")
                    exceptions.append(f"Error connecting to endpoint {endpoint}: {str(ex)}")
        
        # If we get here, all validation attempts failed
        error_detail = "\n".join(exceptions)
        logger.error(f"All token validation attempts failed:\n{error_detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {error_detail}"
        )

    async def get_current_user(self, request: Request) -> UserAuth:
        """
        Get the current authenticated user
        
        Args:
            request: The FastAPI request
            
        Returns:
            UserAuth: The authenticated user information
            
        Raises:
            HTTPException: If not authenticated
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("No Authorization header in request")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Extract token from header
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
        
        # Validate token
        try:
            return await self.validate_token(token)
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )

    async def _test_endpoints(self, token: Optional[str] = None) -> List[EndpointTestResult]:
        """
        Test connection to backend endpoints
        
        Args:
            token: Optional token to include in requests
            
        Returns:
            List[EndpointTestResult]: Results of endpoint tests
        """
        results = []
        headers = {}
        
        # Add Authorization header if token provided
        if token:
            if token.startswith("Bearer "):
                headers["Authorization"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
            
            logger.debug(f"Testing endpoints with Authorization header: {headers['Authorization'][:15]}...")
        else:
            logger.debug("Testing endpoints without Authorization header")
        
        # Test all endpoints
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Test validation endpoints
            for endpoint in self.validate_endpoints:
                result = await self._test_single_endpoint(client, endpoint, headers)
                results.append(result)
            
            # Test health check endpoints
            for endpoint in self.health_endpoints:
                result = await self._test_single_endpoint(client, endpoint, headers)
                results.append(result)
        
        # Log summary
        success_count = sum(1 for r in results if r.status == "success")
        logger.info(f"Endpoint tests completed: {success_count}/{len(results)} successful")
        
        return results

    async def _test_single_endpoint(
        self, client: httpx.AsyncClient, endpoint: str, headers: Dict[str, str]
    ) -> EndpointTestResult:
        """
        Test a single endpoint
        
        Args:
            client: The HTTP client
            endpoint: The endpoint URL
            headers: Request headers
            
        Returns:
            EndpointTestResult: Result of the endpoint test
        """
        try:
            logger.debug(f"Testing endpoint: {endpoint}")
            response = await client.get(endpoint, headers=headers)
            
            # Process the response
            status_code = response.status_code
            try:
                response_text = json.dumps(response.json())[:200]  # Truncate long responses
            except:
                response_text = response.text[:200]  # Truncate long responses
            
            if 200 <= status_code < 300:
                logger.debug(f"Endpoint {endpoint} test successful: {status_code}")
                return EndpointTestResult(
                    endpoint=endpoint,
                    status="success",
                    message=f"Successfully connected with status {status_code}",
                    response_code=status_code,
                    response_text=response_text
                )
            else:
                logger.warning(f"Endpoint {endpoint} test failed with status {status_code}: {response_text}")
                return EndpointTestResult(
                    endpoint=endpoint,
                    status="error",
                    message=f"Request failed with status {status_code}",
                    response_code=status_code,
                    response_text=response_text
                )
        except Exception as ex:
            logger.error(f"Error testing endpoint {endpoint}: {str(ex)}")
            return EndpointTestResult(
                endpoint=endpoint,
                status="error",
                message=f"Connection error: {str(ex)}"
            )