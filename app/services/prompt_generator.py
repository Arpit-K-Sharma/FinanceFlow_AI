from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import logging

from app.models.models import (
    UserFinancialData, 
    MarketData,
    ChatHistory
)

logger = logging.getLogger(__name__)

class PromptGeneratorService:
    def __init__(self):
        logger.info("PromptGeneratorService initialized")
    
    def generate_financial_advice_prompt(self, user_data: UserFinancialData, market_data: MarketData, user_message: Optional[str] = None) -> str:
        """
        Creates a structured prompt for the LLM with user and market data
        """
        try:
            # Format user's financial allocation
            allocation = f"{user_data.profile.savingsPercent}% savings, {user_data.profile.expensesPercent}% expenses, {user_data.profile.investmentsPercent}% investments"
            
            # Format top expense categories
            top_expense_categories = []
            if user_data.expense_categories:
                top_expense_categories = [f"{cat.category} ({cat.percentage:.1f}%)" for cat in user_data.expense_categories[:3]]
            
            # Format investment summary
            investment_status = (
                f"Total invested: ${user_data.investment_summary.totalInvested:.2f}, "
                f"Total return: ${user_data.investment_summary.totalReturn:.2f}, "
                f"Active investments: {user_data.investment_summary.activeInvestments}, "
                f"Top types: {', '.join(user_data.investment_summary.topTypes)}"
            )
            
            # Format saving goals
            goals_status = (
                f"{user_data.goals_summary.activeGoals} active goals, "
                f"{user_data.goals_summary.completedGoals} completed goals, "
                f"Progress: ${user_data.goals_summary.totalCurrentAmount:.2f}/${user_data.goals_summary.totalTargetAmount:.2f}, "
                f"Top categories: {', '.join(user_data.goals_summary.topCategories)}"
            )
            
            # Format market indices
            indices_info = ""
            if market_data.indices:
                indices_info = ", ".join([f"{idx.name}: {idx.value:.2f} ({'+' if idx.percentChange > 0 else ''}{idx.percentChange:.2f}%)" for idx in market_data.indices])
            
            # Format interest rates
            rates_info = ""
            if market_data.interest_rates:
                rates_info = ", ".join([f"{rate.name}: {rate.rate:.2f}% ({'+' if rate.change > 0 else ''}{rate.change:.2f}%)" for rate in market_data.interest_rates])
            
            # Format news headlines with sentiment
            news_text = ""
            if market_data.news_headlines:
                news_items = [f"{news.title} [{news.sentiment}]" for news in market_data.news_headlines[:5]]
                news_text = "\n      - ".join(news_items)
            
            # Add user's specific question if provided
            user_specific_request = ""
            if user_message:
                user_specific_request = f"""
            # USER'S SPECIFIC REQUEST
            The user has asked: "{user_message}"
            
            THIS IS VERY IMPORTANT: You must directly and explicitly address this specific request in your advice. Prioritize answering this question with concrete, data-driven advice tailored to their financial situation. Make the connection between their question and your recommendations clear and obvious.
            
            In addition to addressing their specific question, also provide a comprehensive financial assessment.
            """
            
            # Create system prompt
            prompt = f"""
            As a financial advisor, analyze the following data and provide personalized advice.
            
            # UNDERSTANDING THE FINANCIAL MODEL
            This is a wealth management application where:
            - Income is received and then immediately distributed into designated accounts (savings, expenses, investments)
            - "Available Income" represents only the undistributed income, typically near zero after allocation
            - "Expenses" value represents the amount allocated to the expenses account, NOT total spent
            - "Spending Trend" reflects actual expenses made over time, not account balance
            
            # USER FINANCIAL PROFILE
            - Name: {user_data.profile.name}
            - Current Account Balances:
              - Savings Account: ${user_data.sections.savings:.2f}
              - Expenses Account: ${user_data.sections.expenses:.2f}
              - Investments Account: ${user_data.sections.investments:.2f}
              - Unallocated Income: ${user_data.sections.income:.2f}
            - Income Distribution Policy: {allocation}
            - Leftover allocation preference: {user_data.profile.leftoverAction or "Not set"}
            
            # RECENT ACTIVITY
            - Top Expense Categories: {', '.join(top_expense_categories) if top_expense_categories else "No expense data available"}
            - Monthly Spending Trend: {user_data.spending_trend.direction} by {user_data.spending_trend.percentChange:.1f}% over {user_data.spending_trend.timePeriod}
            - Savings Goals: {goals_status}
            - Investment Portfolio: {investment_status}
            
            # MARKET CONTEXT
            - Market Indices: {indices_info or "Data unavailable"}
            - Current Interest Rates: {rates_info or "Data unavailable"}
            - Inflation Rate: {market_data.inflation:.2f}%
            - Recent Financial News:
              - {news_text or "No recent financial news available"}
            {user_specific_request}
            
            Based on this comprehensive financial data, provide personalized financial advice including:
            1. Insights about spending TRENDS, not just current account balances
            2. Analysis of how this month's spending compares to previous periods
            3. Specific recommendations for better allocation of funds based on spending patterns and financial goals
            4. Investment strategies considering current portfolio and market conditions
            5. Suggestions for improving progress toward savings goals
            6. High-priority actions the user should consider taking in the next 30 days
            
            IMPORTANT: Do NOT compare "Available Income" with expenses - this would be misleading. Focus on spending trends and patterns over time instead.
            
            Your advice should be practical, actionable, and tailored to this specific financial situation. Focus on realistic steps that can improve the user's financial health both short-term and long-term.
            
            Format the response as JSON with the following structure:
            {{
              "insights": [
                {{
                  "title": "Brief, attention-grabbing insight title",
                  "description": "Detailed explanation of the insight with specific data points",
                  "priority": "high|medium|low"
                }}
              ],
              "recommendations": [
                {{
                  "category": "savings|expenses|investments",
                  "action": "Specific action the user should take",
                  "reasoning": "Why this action would benefit the user's financial situation"
                }}
              ],
              "market_context": "Brief analysis of how current market conditions affect this user's finances",
              "summary": "Brief overall summary of financial health and next steps"
            }}
            
            Provide at least 3-5 insights and 3-5 recommendations. Ensure the advice is grounded in the specific data provided.
            
            IMPORTANT CONSTRAINTS:
            1. All recommendation categories MUST be EXACTLY one of these three values: "savings", "expenses", or "investments". No other values are allowed.
            2. If you have a recommendation about income distribution or allocation, categorize it under "expenses" or "savings" depending on the nature of the advice.
            3. Make sure all priorities for insights are exactly "high", "medium", or "low".
            """
            
            logger.debug("Generated financial advice prompt")
            return prompt
        except Exception as e:
            logger.error(f"Error generating financial advice prompt: {str(e)}")
            # Return a simplified fallback prompt
            return """
            As a financial advisor, provide personalized financial advice based on the user's data.
            
            Format the response as JSON with the following structure:
            {
              "insights": [
                {
                  "title": "Brief, attention-grabbing insight title",
                  "description": "Detailed explanation of the insight with specific data points",
                  "priority": "high|medium|low"
                }
              ],
              "recommendations": [
                {
                  "category": "savings|expenses|investments",
                  "action": "Specific action the user should take",
                  "reasoning": "Why this action would benefit the user's financial situation"
                }
              ],
              "market_context": "Brief analysis of how current market conditions affect this user's finances",
              "summary": "Brief overall summary of financial health and next steps"
            }
            
            IMPORTANT: Each recommendation's category MUST be EXACTLY one of: "savings", "expenses", or "investments". No other values are allowed.
            """
    
    def generate_chat_prompt(self, user_data: UserFinancialData, market_data: MarketData, user_message: str, chat_history: List[ChatHistory]) -> str:
        """
        Creates a prompt for chat interaction with financial context
        """
        try:
            # Format user financial data summary (simplified version)
            financial_summary = f"""
            Financial Summary:
            - Savings Account Balance: ${user_data.sections.savings:.2f}
            - Expenses Account Balance: ${user_data.sections.expenses:.2f}
            - Investments Account Balance: ${user_data.sections.investments:.2f}
            - Unallocated Income: ${user_data.sections.income:.2f}
            """
            
            # Add spending trend if available
            if hasattr(user_data, 'spending_trend') and user_data.spending_trend:
                financial_summary += f"- Monthly Spending Trend: {user_data.spending_trend.direction} by {user_data.spending_trend.percentChange:.1f}% over {user_data.spending_trend.timePeriod}\n"
            
            # Add top spending categories if available
            if user_data.expense_categories:
                financial_summary += f"- Top spending categories: {', '.join([cat.category for cat in user_data.expense_categories[:2]])}\n"
            
            # Add goals if available
            if user_data.goals_summary.activeGoals > 0:
                financial_summary += f"- Active savings goals: {user_data.goals_summary.activeGoals}\n"
            
            # Add market info if available
            if market_data.indices and len(market_data.indices) > 0:
                financial_summary += f"- Market condition: {market_data.indices[0].name} is {market_data.indices[0].percentChange:.2f}% today\n"
            
            financial_summary += f"- Current inflation: {market_data.inflation:.2f}%\n"
            
            # Format chat history
            history_text = ""
            for message in chat_history:
                role = "User" if message.role == "user" else "You"
                history_text += f"{role}: {message.content}\n"
            
            # Create system prompt
            prompt = f"""
            You are a helpful, friendly financial assistant. You have access to the user's financial information and can provide personalized advice.
            
            IMPORTANT CONTEXT: In this wealth management application, income is distributed into different accounts (savings, expenses, investments). 
            The account balances represent available funds in each category, not spending history. Focus on spending trends rather than comparing 
            account balances when providing advice.
            
            {financial_summary}
            
            Chat History:
            {history_text}
            
            User's latest message: {user_message}
            
            Respond conversationally and helpfully to the user's message. If their question is about their finances, provide specific advice based on their data. If they ask about market conditions or financial concepts, explain them clearly. Keep your tone friendly and supportive, not judgmental about their financial choices.
            
            Don't explicitly reference having access to their financial data in a way that would sound creepy - just incorporate the information naturally into your helpful advice.
            
            Prioritize giving actionable advice that's specifically relevant to their financial situation.
            """
            
            logger.debug("Generated chat prompt")
            return prompt
        except Exception as e:
            logger.error(f"Error generating chat prompt: {str(e)}")
            # Return a simplified fallback prompt
            return f"""
            You are a helpful financial assistant. The user is asking: "{user_message}"
            
            Please respond in a conversational and helpful way.
            """