import json
import logging
import os
from typing import Dict, List, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str, model: str = None):
        """
        Initialize the LLM service with Google Gemini
        
        Parameters:
        - api_key: Google Gemini API key
        - model: LLM model to use (defaults to environment variable LLM_MODEL or "gemini-pro" if not set)
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        # Use provided model, or get from environment, or fall back to "gemini-pro"
        self.model = model or os.getenv("LLM_MODEL", "gemini-pro")
        logger.info(f"Initializing LLMService with model: {self.model}")
        self.genai = genai
    
    async def generate_financial_advice(self, prompt: str) -> Dict[str, Any]:
        """
        Calls Google Gemini API to generate financial advice
        
        Parameters:
        - prompt: Structured prompt for the LLM
        
        Returns:
        - Dictionary with financial advice
        """
        try:
            # Log the API key status (masked for security)
            api_key_status = "Not Set" if not self.api_key else f"Set (starts with {self.api_key[:4]}...)"
            logger.info(f"Gemini API key status: {api_key_status}")
            
            # Log prompt length
            logger.info(f"Generating financial advice with prompt of length: {len(prompt)}")
            
            model = self.genai.GenerativeModel(self.model)
            logger.info(f"Using model: {self.model}")
            
            # Add system prompt and user prompt
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            # For Gemini, combine system and user prompts
            system_prompt = "You are a financial analyst with expertise in personal finance. Respond in valid JSON format."
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Log attempt
            logger.info("Sending request to Gemini API...")
            
            try:
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
                logger.info("Received response from Gemini API")
                
                # Parse the JSON response
                try:
                    content = response.text
                    logger.debug(f"LLM response: {content}")
                    
                    # Extract JSON part if the response contains explanatory text
                    if "```json" in content:
                        json_start = content.find("```json") + 7
                        json_end = content.find("```", json_start)
                        content = content[json_start:json_end].strip()
                        logger.debug(f"Extracted JSON content: {content[:100]}...")
                    elif "```" in content:
                        json_start = content.find("```") + 3
                        json_end = content.find("```", json_start)
                        content = content[json_start:json_end].strip()
                        logger.debug(f"Extracted code block content: {content[:100]}...")
                    
                    response_data = json.loads(content)
                    
                    # Validate and fix recommendation categories
                    valid_categories = ["savings", "expenses", "investments"]
                    if "recommendations" in response_data:
                        for i, rec in enumerate(response_data["recommendations"]):
                            if rec.get("category") not in valid_categories:
                                logger.warning(f"Invalid recommendation category: {rec.get('category')}. Defaulting to 'expenses'")
                                # Map invalid categories to a valid one
                                if "income" in rec.get("category", "").lower():
                                    response_data["recommendations"][i]["category"] = "savings"
                                else:
                                    response_data["recommendations"][i]["category"] = "expenses"
                    
                    # Validate insight priorities
                    valid_priorities = ["high", "medium", "low"]
                    if "insights" in response_data:
                        for i, insight in enumerate(response_data["insights"]):
                            if insight.get("priority") not in valid_priorities:
                                logger.warning(f"Invalid insight priority: {insight.get('priority')}. Defaulting to 'medium'")
                                response_data["insights"][i]["priority"] = "medium"
                    
                    return response_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON: {e}")
                    logger.error(f"Raw response content: {content}")
                    return self._fallback_advice_response("Failed to generate proper financial advice. Please try again later.")
            except Exception as api_error:
                logger.error(f"Specific Gemini API error: {str(api_error)}")
                raise  # Re-raise to be caught by outer exception handler
                
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}", exc_info=True)
            return self._fallback_advice_response(f"Error generating financial advice: {str(e)}")
    
    async def generate_chat_response(self, prompt: str) -> str:
        """
        Generates a conversational response for the chat interface
        
        Parameters:
        - prompt: Prompt containing user message and context
        
        Returns:
        - String response for the chat
        """
        try:
            # Log the API key status (masked for security)
            api_key_status = "Not Set" if not self.api_key else f"Set (starts with {self.api_key[:4]}...)"
            logger.info(f"Gemini API key status: {api_key_status}")
            
            # Log prompt length
            logger.info(f"Generating chat response with prompt of length: {len(prompt)}")
            
            model = self.genai.GenerativeModel(self.model)
            logger.info(f"Using model: {self.model}")
            
            system_prompt = "You are a helpful financial assistant."
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Log the attempt
            logger.info("Sending request to Gemini API...")
            
            try:
                response = model.generate_content(full_prompt)
                logger.info("Received response from Gemini API")
                
                content = response.text
                logger.debug(f"Chat response: {content}")
                return content
            except Exception as api_error:
                logger.error(f"Specific Gemini API error: {str(api_error)}")
                raise  # Re-raise to be caught by outer exception handler
                
        except Exception as e:
            logger.error(f"Gemini API error in chat response: {str(e)}", exc_info=True)
            return "I'm sorry, I'm having trouble connecting to my knowledge base right now. Please try again in a moment."
    
    def _fallback_advice_response(self, error_message: str) -> Dict[str, Any]:
        """
        Creates a fallback response when advice generation fails
        
        Parameters:
        - error_message: Error message to include
        
        Returns:
        - Dictionary with basic fallback advice
        """
        return {
            "insights": [
                {
                    "title": "Service Temporarily Unavailable",
                    "description": error_message,
                    "priority": "high"
                },
                {
                    "title": "General Financial Advice",
                    "description": "Consider keeping an emergency fund of 3-6 months of expenses, pay off high-interest debt, and save at least 15-20% of your income.",
                    "priority": "medium"
                }
            ],
            "recommendations": [
                {
                    "category": "savings",
                    "action": "Ensure you have an emergency fund covering 3-6 months of expenses",
                    "reasoning": "This provides financial security during unexpected events"
                },
                {
                    "category": "expenses",
                    "action": "Track your spending for the next 30 days to identify areas for improvement",
                    "reasoning": "Understanding your spending habits is the first step to optimizing your budget"
                },
                {
                    "category": "investments",
                    "action": "Consider diversifying your investments across different asset classes",
                    "reasoning": "Diversification can help reduce risk while maintaining returns"
                }
            ],
            "market_context": "Financial markets experience regular fluctuations. Focus on your long-term financial goals rather than short-term market movements.",
            "summary": "While personalized advice is temporarily unavailable, focus on building emergency savings, reducing high-interest debt, and saving consistently for long-term goals."
        }