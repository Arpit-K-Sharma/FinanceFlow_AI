import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging

from app.models.models import (
    UserFinancialData, 
    UserProfile, 
    SectionData, 
    Transaction, 
    Expense, 
    Investment, 
    SavingGoal,
    ExpenseCategory,
    InvestmentSummary,
    GoalsSummary,
    SpendingTrend
)

logger = logging.getLogger(__name__)

class DataAggregatorService:
    def __init__(self, base_url: Optional[str] = None):
    # Ensure base_url doesn't end with a slash
        if base_url is None:
            # Provide a default URL or raise a more descriptive error
            logger.error("No base_url provided. Check if BACKEND_URL is set in environment variables.")
            self.base_url = "http://localhost:8000"  # Or another default URL
        else:
            self.base_url = base_url.rstrip('/')
        
        logger.info(f"DataAggregatorService initialized with base URL: {self.base_url}")
        
    async def get_user_financial_data(self, user_id: str, user_token: str) -> UserFinancialData:
        """
        Aggregate all financial data for a user from the main backend
        """
        try:
            headers = {"Authorization": f"Bearer {user_token}"}
            
            # Create aiohttp ClientSession to reuse connections
            async with aiohttp.ClientSession() as session:
                # Fetch all data in parallel
                profile, sections, transactions, expenses, investments, goals = await asyncio.gather(
                    self._fetch_profile(session, user_id, headers),
                    self._fetch_sections(session, headers),
                    self._fetch_transactions(session, headers, limit=30),
                    self._fetch_expenses(session, headers),
                    self._fetch_investments(session, headers),
                    self._fetch_saving_goals(session, headers)
                )
                
                # Calculate derived data
                expense_categories = self._process_expense_categories(expenses)
                investment_summary = self._process_investments(investments)
                goals_summary = self._process_goals(goals)
                spending_trend = self._calculate_spending_trend(expenses)
                
                # Return consolidated user financial data
                return UserFinancialData(
                    user_id=user_id,
                    profile=profile,
                    sections=sections,
                    recent_transactions=transactions,
                    expense_categories=expense_categories,
                    investment_summary=investment_summary,
                    goals_summary=goals_summary,
                    spending_trend=spending_trend,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error fetching user financial data: {str(e)}")
            raise
    
    async def _fetch_profile(self, session, user_id: str, headers: Dict) -> UserProfile:
        """
        Fetch user profile data
        """
        try:
            async with session.get(f"{self.base_url}/api/users/profile", headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Error fetching profile: Status {response.status}, {text}")
                    raise Exception(f"Failed to fetch profile: {response.status}")
                
                data = await response.json()
                
                # Handle FinanceFlow response format which wraps data in a data field
                if isinstance(data, dict):
                    if "data" in data:
                        profile_data = data["data"]
                    elif "status" in data and data["status"] == "success":
                        profile_data = data.get("data", {})
                    else:
                        profile_data = data
                else:
                    profile_data = {}
                
                # Ensure required fields exist
                user_profile = UserProfile(
                    id=profile_data.get("id", user_id),
                    name=profile_data.get("name", "User"),
                    email=profile_data.get("email", "unknown@example.com"),
                    savingsPercent=profile_data.get("savingsPercent", 0),
                    expensesPercent=profile_data.get("expensesPercent", 0),
                    investmentsPercent=profile_data.get("investmentsPercent", 0),
                    leftoverAction=profile_data.get("leftoverAction"),
                    isEmailVerified=profile_data.get("isEmailVerified", False)
                )
                
                return user_profile
        except Exception as e:
            logger.error(f"Error in _fetch_profile: {str(e)}")
            # Return minimal profile to prevent complete failure
            return UserProfile(
                id=user_id,
                name="Unknown",
                email="unknown@example.com"
            )
    
    async def _fetch_sections(self, session, headers: Dict) -> SectionData:
        """
        Fetch financial sections data
        """
        try:
            async with session.get(f"{self.base_url}/api/sections", headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error fetching sections: Status {response.status}")
                    return SectionData()
                
                data = await response.json()
                
                # Handle different response formats
                if isinstance(data, dict):
                    section_data = data  # Default to full response
                    
                    if "data" in data:
                        section_data = data.get("data", {})
                    elif "status" in data and data["status"] == "success":
                        section_data = data.get("data", {})
                else:
                    section_data = {}
                
                # Get income if available
                income = 0
                try:
                    income_response = await session.get(f"{self.base_url}/api/income/available", headers=headers)
                    if income_response.status == 200:
                        income_data = await income_response.json()
                        if isinstance(income_data, dict):
                            if "data" in income_data:
                                income = income_data.get("data", 0)
                            elif "status" in income_data and income_data["status"] == "success":
                                income = income_data.get("data", 0)
                except Exception as e:
                    logger.warning(f"Error fetching income: {str(e)}")
                
                return SectionData(
                    savings=section_data.get("savings", 0),
                    expenses=section_data.get("expenses", 0),
                    investments=section_data.get("investments", 0),
                    income=income
                )
        except Exception as e:
            logger.error(f"Error in _fetch_sections: {str(e)}")
            return SectionData()
    
    async def _fetch_transactions(self, session, headers: Dict, limit: int = 10) -> List[Transaction]:
        """
        Fetch recent transactions
        """
        try:
            async with session.get(f"{self.base_url}/api/transactions?limit={limit}", headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error fetching transactions: Status {response.status}")
                    return []
                
                data = await response.json()
                
                # Handle different response formats
                transactions_data = []
                
                if isinstance(data, dict):
                    if "data" in data:
                        transactions_data = data.get("data", [])
                    elif "status" in data and data["status"] == "success":
                        transactions_data = data.get("data", [])
                elif isinstance(data, list):
                    transactions_data = data
                
                # Convert to Transaction objects with error handling
                transactions = []
                for transaction in transactions_data:
                    try:
                        transactions.append(Transaction(**transaction))
                    except Exception as e:
                        logger.warning(f"Error parsing transaction data: {str(e)}")
                
                return transactions
        except Exception as e:
            logger.error(f"Error in _fetch_transactions: {str(e)}")
            return []
    
    async def _fetch_expenses(self, session, headers: Dict) -> List[Expense]:
        """
        Fetch expenses
        """
        try:
            async with session.get(f"{self.base_url}/api/expenses?limit=50", headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error fetching expenses: Status {response.status}")
                    return []
                
                data = await response.json()
                
                # Handle different response formats
                expenses_data = []
                
                if isinstance(data, dict):
                    if "data" in data:
                        expenses_data = data.get("data", [])
                    elif "status" in data and data["status"] == "success":
                        expenses_data = data.get("data", [])
                elif isinstance(data, list):
                    expenses_data = data
                
                # Convert to Expense objects with error handling
                expenses = []
                for expense in expenses_data:
                    try:
                        expenses.append(Expense(**expense))
                    except Exception as e:
                        logger.warning(f"Error parsing expense data: {str(e)}")
                
                return expenses
        except Exception as e:
            logger.error(f"Error in _fetch_expenses: {str(e)}")
            return []
    
    async def _fetch_investments(self, session, headers: Dict) -> List[Investment]:
        """
        Fetch investments
        """
        try:
            async with session.get(f"{self.base_url}/api/investments", headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error fetching investments: Status {response.status}")
                    return []
                
                data = await response.json()
                
                # Handle different response formats
                investments_data = []
                
                if isinstance(data, dict):
                    if "data" in data:
                        investments_data = data.get("data", [])
                    elif "status" in data and data["status"] == "success":
                        investments_data = data.get("data", [])
                elif isinstance(data, list):
                    investments_data = data
                
                # Convert to Investment objects with error handling
                investments = []
                for investment in investments_data:
                    try:
                        investments.append(Investment(**investment))
                    except Exception as e:
                        logger.warning(f"Error parsing investment data: {str(e)}")
                
                return investments
        except Exception as e:
            logger.error(f"Error in _fetch_investments: {str(e)}")
            return []
    
    async def _fetch_saving_goals(self, session, headers: Dict) -> List[SavingGoal]:
        """
        Fetch saving goals
        """
        try:
            async with session.get(f"{self.base_url}/api/saving-goals", headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error fetching saving goals: Status {response.status}")
                    return []
                
                data = await response.json()
                
                # Handle different response formats
                goals_data = []
                
                if isinstance(data, dict):
                    if "data" in data:
                        goals_data = data.get("data", [])
                    elif "status" in data and data["status"] == "success":
                        goals_data = data.get("data", [])
                elif isinstance(data, list):
                    goals_data = data
                
                # Convert to SavingGoal objects with error handling
                goals = []
                for goal in goals_data:
                    try:
                        goals.append(SavingGoal(**goal))
                    except Exception as e:
                        logger.warning(f"Error parsing saving goal data: {str(e)}")
                
                return goals
        except Exception as e:
            logger.error(f"Error in _fetch_saving_goals: {str(e)}")
            return []
    
    def _process_expense_categories(self, expenses: List[Expense]) -> List[ExpenseCategory]:
        """
        Process expenses to get category breakdown
        """
        if not expenses:
            return []
        
        # Group expenses by category
        categories = {}
        total_amount = 0
        
        for expense in expenses:
            category = expense.category or "Uncategorized"
            if category not in categories:
                categories[category] = 0
            categories[category] += expense.amount
            total_amount += expense.amount
        
        # Calculate percentages and sort by amount
        result = []
        for category, amount in categories.items():
            percentage = (amount / total_amount * 100) if total_amount > 0 else 0
            result.append(ExpenseCategory(
                category=category,
                amount=amount,
                percentage=percentage
            ))
        
        # Sort by amount descending
        return sorted(result, key=lambda x: x.amount, reverse=True)
    
    def _process_investments(self, investments: List[Investment]) -> InvestmentSummary:
        """
        Process investments to get summary
        """
        if not investments:
            return InvestmentSummary(
                totalInvested=0,
                totalReturn=0,
                activeInvestments=0,
                closedInvestments=0,
                topTypes=[]
            )
        
        total_invested = 0
        total_return = 0
        active_investments = 0
        closed_investments = 0
        
        # Group by investment type
        types = {}
        
        for investment in investments:
            total_invested += investment.amount
            total_return += investment.totalReturn
            
            if investment.isClosed:
                closed_investments += 1
            else:
                active_investments += 1
            
            inv_type = investment.investmentType or "Other"
            if inv_type not in types:
                types[inv_type] = 0
            types[inv_type] += 1
        
        # Get top investment types
        top_types = sorted(types.items(), key=lambda x: x[1], reverse=True)
        top_types = [t[0] for t in top_types[:3]]  # Take top 3
        
        return InvestmentSummary(
            totalInvested=total_invested,
            totalReturn=total_return,
            activeInvestments=active_investments,
            closedInvestments=closed_investments,
            topTypes=top_types
        )
    
    def _process_goals(self, goals: List[SavingGoal]) -> GoalsSummary:
        """
        Process saving goals to get summary
        """
        if not goals:
            return GoalsSummary(
                totalGoals=0,
                activeGoals=0,
                completedGoals=0,
                totalTargetAmount=0,
                totalCurrentAmount=0,
                topCategories=[]
            )
        
        total_goals = len(goals)
        active_goals = 0
        completed_goals = 0
        total_target = 0
        total_current = 0
        
        # Group by category
        categories = {}
        
        for goal in goals:
            total_target += goal.targetAmount
            total_current += goal.currentAmount
            
            if goal.isCompleted:
                completed_goals += 1
            else:
                active_goals += 1
            
            category = goal.category or "Other"
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        # Get top categories
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top_categories = [c[0] for c in top_categories[:3]]  # Take top 3
        
        return GoalsSummary(
            totalGoals=total_goals,
            activeGoals=active_goals,
            completedGoals=completed_goals,
            totalTargetAmount=total_target,
            totalCurrentAmount=total_current,
            topCategories=top_categories
        )
    
    def _calculate_spending_trend(self, expenses: List[Expense]) -> SpendingTrend:
        """
        Calculate spending trend over time with more detailed analysis
        """
        if not expenses or len(expenses) < 2:
            return SpendingTrend(
                direction="stable",
                percentChange=0,
                timePeriod="30 days",
                monthlyTotals={},
                totalSpent=0,
                averageExpense=0
            )
        
        try:
            # Sort expenses by date
            sorted_expenses = sorted(expenses, key=lambda x: x.createdAt)
            
            # Calculate total spent and average expense
            total_spent = sum(expense.amount for expense in expenses)
            average_expense = total_spent / len(expenses)
            
            # Group by month
            months = {}
            for expense in sorted_expenses:
                month_key = expense.createdAt.strftime("%Y-%m")
                if month_key not in months:
                    months[month_key] = 0
                months[month_key] += expense.amount
            
            # Need at least two months to calculate trend
            if len(months) < 2:
                return SpendingTrend(
                    direction="stable",
                    percentChange=0,
                    timePeriod="30 days",
                    monthlyTotals=months,
                    totalSpent=total_spent,
                    averageExpense=average_expense
                )
            
            # Get last two months
            month_keys = sorted(months.keys())
            current_month = months[month_keys[-1]]
            prev_month = months[month_keys[-2]]
            
            # Calculate percent change
            percent_change = ((current_month - prev_month) / prev_month * 100) if prev_month > 0 else 0
            
            # Get month-over-month trend for past 3 months if available
            trend_description = "month-to-month"
            if len(month_keys) >= 3:
                trend_description = f"over the past {len(month_keys)} months"
            
            # Determine direction
            if percent_change > 5:
                direction = "increasing"
            elif percent_change < -5:
                direction = "decreasing"
            else:
                direction = "stable"
            
            return SpendingTrend(
                direction=direction,
                percentChange=abs(percent_change),
                timePeriod=trend_description,
                monthlyTotals=months,
                totalSpent=total_spent,
                averageExpense=average_expense
            )
        except Exception as e:
            logger.error(f"Error calculating spending trend: {str(e)}")
            return SpendingTrend(
                direction="stable",
                percentChange=0,
                timePeriod="30 days",
                monthlyTotals={},
                totalSpent=0,
                averageExpense=0
            )