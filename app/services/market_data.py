import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import json
import random  # For mock data

from app.models.models import (
    MarketData,
    MarketIndex,
    NewsHeadline,
    InterestRate
)

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, api_keys: Dict[str, str]):
        """
        Initialize the market data service with API keys
        
        Parameters:
        - api_keys: Dictionary with keys for different financial APIs
          e.g., {"alpha_vantage": "your_key", "news_api": "your_key"}
        """
        self.api_keys = api_keys
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
        logger.info("MarketDataService initialized")
    
    async def get_market_summary(self) -> MarketData:
        """
        Get current market data from external APIs
        """
        try:
            # Check if we have cached data that's still valid
            if "market_summary" in self.cache and datetime.now().timestamp() < self.cache_expiry.get("market_summary", 0):
                logger.info("Returning cached market data")
                return self.cache["market_summary"]
            
            logger.info("Fetching fresh market data")
            # Fetch all data in parallel
            indices, news, rates, inflation = await asyncio.gather(
                self._fetch_market_indices(),
                self._fetch_financial_news(),
                self._fetch_interest_rates(),
                self._fetch_inflation_data()
            )
            
            # Create market data object
            market_data = MarketData(
                indices=indices,
                news_headlines=news,
                interest_rates=rates,
                inflation=inflation,
                timestamp=datetime.now()
            )
            
            # Cache the data
            self.cache["market_summary"] = market_data
            self.cache_expiry["market_summary"] = datetime.now().timestamp() + self.cache_duration
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            # Return mock data in case of failure
            return self._get_mock_market_data()
    
    async def _fetch_market_indices(self) -> List[MarketIndex]:
        """
        Fetch major market indices (S&P 500, Dow Jones, NASDAQ)
        """
        indices = []
        
        try:
            alpha_vantage_key = self.api_keys.get("alpha_vantage")
            if not alpha_vantage_key:
                logger.warning("No Alpha Vantage API key provided, using mock data")
                return self._get_mock_indices()
            
            # List of indices to fetch (symbol, name)
            index_list = [
                ("^GSPC", "S&P 500"),
                ("^DJI", "Dow Jones"),
                ("^IXIC", "NASDAQ")
            ]
            
            async with aiohttp.ClientSession() as session:
                for symbol, name in index_list:
                    try:
                        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
                        logger.debug(f"Requesting data for {name} from Alpha Vantage")
                        
                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.warning(f"Failed to fetch data for {name}: Status {response.status}")
                                continue
                            
                            data = await response.json()
                            
                            # Check for API limit error
                            if "Note" in data and "API call frequency" in data["Note"]:
                                logger.warning(f"Alpha Vantage API limit reached: {data['Note']}")
                                return self._get_mock_indices()
                                
                            if "Global Quote" not in data:
                                logger.warning(f"Invalid response format for {name}: {data}")
                                continue
                            
                            quote = data["Global Quote"]
                            
                            # Check if we have all required fields
                            required_fields = ["05. price", "09. change", "10. change percent"]
                            if not all(field in quote for field in required_fields):
                                logger.warning(f"Missing required fields in response for {name}: {quote}")
                                continue
                            
                            # Extract data
                            try:
                                value = float(quote.get("05. price", 0))
                                change = float(quote.get("09. change", 0))
                                percent_change = float(quote.get("10. change percent", "0").replace("%", ""))
                                
                                indices.append(MarketIndex(
                                    name=name,
                                    value=value,
                                    change=change,
                                    percentChange=percent_change
                                ))
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing values for {name}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error fetching {name} index: {str(e)}")
            
            # If we couldn't fetch any indices, use mock data
            if not indices:
                logger.warning("No indices successfully fetched, using mock data")
                return self._get_mock_indices()
                
            return indices
                
        except Exception as e:
            logger.error(f"Error in _fetch_market_indices: {str(e)}")
            return self._get_mock_indices()
    
    async def _fetch_financial_news(self) -> List[NewsHeadline]:
        """
        Fetch financial news headlines
        """
        try:
            news_api_key = self.api_keys.get("news_api")
            if not news_api_key:
                logger.warning("No News API key provided, using mock data")
                return self._get_mock_news()
            
            logger.debug("Requesting financial news from News API")
            async with aiohttp.ClientSession() as session:
                url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={news_api_key}"
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch financial news: Status {response.status}")
                        return self._get_mock_news()
                    
                    data = await response.json()
                    
                    # Check for API errors
                    if "status" in data and data["status"] != "ok":
                        logger.warning(f"News API error: {data.get('message', 'Unknown error')}")
                        return self._get_mock_news()
                        
                    if "articles" not in data:
                        logger.warning("Invalid news API response format")
                        return self._get_mock_news()
                    
                    articles = data["articles"]
                    if not articles:
                        logger.warning("No articles returned from News API")
                        return self._get_mock_news()
                        
                    headlines = []
                    
                    for article in articles[:10]:  # Take top 10 articles
                        # Simple sentiment analysis based on title
                        try:
                            title = article.get("title", "")
                            if not title:
                                continue
                                
                            sentiment = self._analyze_sentiment(title)
                            
                            headlines.append(NewsHeadline(
                                title=title,
                                source=article.get("source", {}).get("name", "Unknown"),
                                url=article.get("url"),
                                sentiment=sentiment
                            ))
                        except Exception as e:
                            logger.warning(f"Error processing news article: {str(e)}")
                    
                    if not headlines:
                        logger.warning("No valid headlines extracted")
                        return self._get_mock_news()
                        
                    return headlines
                    
        except Exception as e:
            logger.error(f"Error in _fetch_financial_news: {str(e)}")
            return self._get_mock_news()
    
    async def _fetch_interest_rates(self) -> List[InterestRate]:
        """
        Fetch current interest rates
        """
        try:
            # Use FRED API (Federal Reserve Economic Data) if available
            fred_api_key = self.api_keys.get("fred_api")
            
            if fred_api_key:
                rates = []
                series_ids = {
                    "DFF": "Federal Funds Rate",
                    "MORTGAGE30US": "30-Year Fixed Mortgage Rate",
                    "TB3MS": "3-Month Treasury Bill"
                }
                
                logger.debug("Requesting interest rates from FRED API")
                async with aiohttp.ClientSession() as session:
                    for series_id, name in series_ids.items():
                        try:
                            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={fred_api_key}&file_type=json&sort_order=desc&limit=2"
                            async with session.get(url) as response:
                                if response.status != 200:
                                    logger.warning(f"Failed to fetch {name} rate: Status {response.status}")
                                    continue
                                
                                data = await response.json()
                                
                                # Check for API errors
                                if "error_code" in data:
                                    logger.warning(f"FRED API error for {name}: {data.get('error_message', 'Unknown error')}")
                                    continue
                                    
                                if "observations" not in data or len(data["observations"]) < 2:
                                    logger.warning(f"Invalid response for {name} rate")
                                    continue
                                
                                observations = data["observations"]
                                
                                # Check for valid values
                                if not all("value" in obs for obs in observations[:2]):
                                    logger.warning(f"Missing values in response for {name}")
                                    continue
                                    
                                # Convert values to float, handling "." for missing data
                                try:
                                    current_value = observations[0]["value"]
                                    previous_value = observations[1]["value"]
                                    
                                    current = float(current_value) if current_value != "." else 0
                                    previous = float(previous_value) if previous_value != "." else 0
                                    change = current - previous
                                    
                                    rates.append(InterestRate(
                                        name=name,
                                        rate=current,
                                        change=change
                                    ))
                                except (ValueError, TypeError) as e:
                                    logger.error(f"Error parsing values for {name}: {str(e)}")
                        except Exception as e:
                            logger.error(f"Error fetching {name} rate: {str(e)}")
                
                # If we fetched any rates, return them
                if rates:
                    return rates
                    
                logger.warning("No interest rates successfully fetched, using mock data")
            else:
                logger.warning("No FRED API key provided, using mock data")
            
            # Otherwise, return mock data
            return self._get_mock_interest_rates()
                
        except Exception as e:
            logger.error(f"Error in _fetch_interest_rates: {str(e)}")
            return self._get_mock_interest_rates()
    
    async def _fetch_inflation_data(self) -> float:
        """
        Fetch current inflation rate
        """
        try:
            # Use FRED API for inflation data if available
            fred_api_key = self.api_keys.get("fred_api")
            
            if fred_api_key:
                logger.debug("Requesting inflation data from FRED API")
                async with aiohttp.ClientSession() as session:
                    # CPI annual change (CPIAUCSL)
                    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key={fred_api_key}&file_type=json&sort_order=desc&limit=13"
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.warning(f"Failed to fetch inflation data: Status {response.status}")
                            return self._get_mock_inflation()
                        
                        data = await response.json()
                        
                        # Check for API errors
                        if "error_code" in data:
                            logger.warning(f"FRED API error for inflation data: {data.get('error_message', 'Unknown error')}")
                            return self._get_mock_inflation()
                            
                        if "observations" not in data or len(data["observations"]) < 13:
                            logger.warning("Invalid response for inflation data")
                            return self._get_mock_inflation()
                        
                        # Check for valid values
                        observations = data["observations"]
                        if not all("value" in obs for obs in [observations[0], observations[12]]):
                            logger.warning("Missing values in inflation data response")
                            return self._get_mock_inflation()
                            
                        # Calculate year-over-year inflation
                        try:
                            current_value = observations[0]["value"]
                            year_ago_value = observations[12]["value"]
                            
                            # Handle missing values (represented as ".")
                            current = float(current_value) if current_value != "." else 0
                            year_ago = float(year_ago_value) if year_ago_value != "." else 0
                            
                            # Avoid division by zero
                            if year_ago == 0:
                                logger.warning("Year ago CPI value is zero or missing")
                                return self._get_mock_inflation()
                                
                            inflation_rate = ((current - year_ago) / year_ago) * 100
                            
                            return round(inflation_rate, 2)
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error calculating inflation rate: {str(e)}")
            else:
                logger.warning("No FRED API key provided for inflation data, using mock data")
            
            # If FRED API key not available or calculation failed, use mock data
            return self._get_mock_inflation()
                
        except Exception as e:
            logger.error(f"Error in _fetch_inflation_data: {str(e)}")
            return self._get_mock_inflation()
    
    def _analyze_sentiment(self, text: str) -> str:
        """
        Simple sentiment analysis based on keywords
        """
        text = text.lower()
        
        positive_words = ['gain', 'rise', 'up', 'grow', 'improve', 'positive', 'rally', 'surge',
                         'jump', 'profit', 'advance', 'recovery', 'strong', 'success', 'boom',
                         'bullish', 'upbeat', 'optimistic', 'higher']
        
        negative_words = ['loss', 'fall', 'down', 'drop', 'decline', 'negative', 'plunge', 'crash',
                         'slump', 'recession', 'bearish', 'weakness', 'weak', 'struggle', 'crisis',
                         'fail', 'cut', 'slash', 'lower', 'fear', 'worry', 'concern']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _get_mock_market_data(self) -> MarketData:
        """
        Generate mock market data
        """
        logger.info("Generating mock market data")
        return MarketData(
            indices=self._get_mock_indices(),
            news_headlines=self._get_mock_news(),
            interest_rates=self._get_mock_interest_rates(),
            inflation=self._get_mock_inflation(),
            timestamp=datetime.now()
        )
    
    def _get_mock_indices(self) -> List[MarketIndex]:
        """
        Generate mock market indices
        """
        return [
            MarketIndex(
                name="S&P 500",
                value=4500 + random.uniform(-50, 50),
                change=random.uniform(-10, 10),
                percentChange=random.uniform(-1, 1)
            ),
            MarketIndex(
                name="Dow Jones",
                value=36000 + random.uniform(-300, 300),
                change=random.uniform(-100, 100),
                percentChange=random.uniform(-1, 1)
            ),
            MarketIndex(
                name="NASDAQ",
                value=15000 + random.uniform(-150, 150),
                change=random.uniform(-50, 50),
                percentChange=random.uniform(-1, 1)
            )
        ]
    
    def _get_mock_news(self) -> List[NewsHeadline]:
        """
        Generate mock financial news headlines
        """
        headlines = [
            NewsHeadline(
                title="FED Raises Interest Rates by 25 Basis Points",
                source="Financial Times",
                url="https://example.com/news/1",
                sentiment="negative"
            ),
            NewsHeadline(
                title="Tech Stocks Rally on Strong Earnings Reports",
                source="Wall Street Journal",
                url="https://example.com/news/2",
                sentiment="positive"
            ),
            NewsHeadline(
                title="Housing Market Shows Signs of Cooling",
                source="Bloomberg",
                url="https://example.com/news/3",
                sentiment="neutral"
            ),
            NewsHeadline(
                title="Inflation Eases for Third Consecutive Month",
                source="CNBC",
                url="https://example.com/news/4",
                sentiment="positive"
            ),
            NewsHeadline(
                title="Oil Prices Stabilize After Recent Volatility",
                source="Reuters",
                url="https://example.com/news/5",
                sentiment="neutral"
            )
        ]
        
        return headlines
    
    def _get_mock_interest_rates(self) -> List[InterestRate]:
        """
        Generate mock interest rates
        """
        return [
            InterestRate(
                name="Federal Funds Rate",
                rate=5.25 + random.uniform(-0.1, 0.1),
                change=0.25
            ),
            InterestRate(
                name="30-Year Fixed Mortgage Rate",
                rate=7.1 + random.uniform(-0.2, 0.2),
                change=0.05
            ),
            InterestRate(
                name="3-Month Treasury Bill",
                rate=4.8 + random.uniform(-0.1, 0.1),
                change=-0.02
            )
        ]
    
    def _get_mock_inflation(self) -> float:
        """
        Generate mock inflation rate
        """
        return round(4.0 + random.uniform(-0.5, 0.5), 2)