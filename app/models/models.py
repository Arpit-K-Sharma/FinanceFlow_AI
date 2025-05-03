from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Literal
from datetime import datetime

class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    savingsPercent: Optional[float] = 0
    expensesPercent: Optional[float] = 0
    investmentsPercent: Optional[float] = 0
    leftoverAction: Optional[str] = None
    isEmailVerified: Optional[bool] = False
    
class SectionData(BaseModel):
    savings: float = 0
    expenses: float = 0
    investments: float = 0
    income: Optional[float] = 0
    
class Transaction(BaseModel):
    id: str
    type: str
    fromSection: Optional[str] = None
    toSection: Optional[str] = None
    amount: float
    description: Optional[str] = None
    createdAt: datetime
    
class Expense(BaseModel):
    id: str
    amount: float
    category: str
    description: Optional[str] = None
    createdAt: datetime
    
class Investment(BaseModel):
    id: str
    assetName: str
    amount: float
    investmentType: str
    totalReturn: float = 0
    isClosed: bool = False
    notes: Optional[str] = None
    createdAt: datetime
    
class SavingGoal(BaseModel):
    id: str
    name: str
    targetAmount: float
    currentAmount: float
    category: str
    transferType: Optional[str] = None
    purpose: Optional[str] = None
    isCompleted: bool = False
    createdAt: datetime
    
class ExpenseCategory(BaseModel):
    category: str
    amount: float
    percentage: float
    
class InvestmentSummary(BaseModel):
    totalInvested: float
    totalReturn: float
    activeInvestments: int
    closedInvestments: int
    topTypes: List[str]
    
class GoalsSummary(BaseModel):
    totalGoals: int
    activeGoals: int
    completedGoals: int
    totalTargetAmount: float
    totalCurrentAmount: float
    topCategories: List[str]
    
class SpendingTrend(BaseModel):
    direction: Literal["increasing", "decreasing", "stable"]
    percentChange: float
    timePeriod: str
    monthlyTotals: Dict[str, float] = Field(default_factory=dict)
    totalSpent: float = 0
    averageExpense: float = 0

class UserFinancialData(BaseModel):
    user_id: str
    profile: UserProfile
    sections: SectionData
    recent_transactions: List[Transaction]
    expense_categories: List[ExpenseCategory]
    investment_summary: InvestmentSummary
    goals_summary: GoalsSummary
    spending_trend: SpendingTrend
    timestamp: datetime

class MarketIndex(BaseModel):
    name: str
    value: float
    change: float
    percentChange: float
    
class NewsHeadline(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    
class InterestRate(BaseModel):
    name: str
    rate: float
    change: float
    
class MarketData(BaseModel):
    indices: List[MarketIndex]
    news_headlines: List[NewsHeadline]
    interest_rates: List[InterestRate]
    inflation: float
    timestamp: datetime

class AIInsight(BaseModel):
    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    
class AIRecommendation(BaseModel):
    category: Literal["savings", "expenses", "investments"]
    action: str
    reasoning: str
    
class FinancialAdvice(BaseModel):
    insights: List[AIInsight]
    recommendations: List[AIRecommendation]
    market_context: str
    summary: str
    
class ChatHistory(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    
class FinancialAdviceRequest(BaseModel):
    user_id: str
    user_token: str
    message: Optional[str] = None
    
class ChatMessage(BaseModel):
    user_id: str
    user_token: str
    content: str
    chat_history: Optional[List[ChatHistory]] = Field(default_factory=list)

# Authentication related models
class UserAuth(BaseModel):
    id: str
    email: str
    is_active: bool = True

# Financial API request models
class AdviceRequest(BaseModel):
    message: Optional[str] = None
    
class ChatRequest(BaseModel):
    content: str
    chat_history: Optional[List[ChatHistory]] = Field(default_factory=list)
    
class ChatResponse(BaseModel):
    response: str