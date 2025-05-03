# Financial AI Assistant API

This API provides AI-powered financial advice and chat capabilities for the Wealth Management application.

## Features

- **Pass-Through Authentication**: Uses backend API tokens passed from the frontend
- **Financial Advice Generation**: Get personalized financial advice based on user data
- **AI Chat Assistant**: Chat with an AI assistant that has context about financial data
- **Market Data Integration**: Financial advice includes current market context

## Quick Start

### Prerequisites

- Python 3.9+
- Virtualenv or similar virtual environment

### Installation

1. Clone the repository:
```
git clone <repository-url>
cd ai-service
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```
# API Configuration
FRONTEND_URL=http://localhost:8080
MAIN_BACKEND_URL=http://localhost:3000/api

# LLM Configuration
GOOGLE_API_KEY=your_google_api_key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro

# External API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
NEWS_API_KEY=your_news_api_key
FRED_API_KEY=your_fred_api_key
```

5. Start the server:
```
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Authentication

- `GET /auth/validate` - Validate a token
- `GET /auth/me` - Get current user information

### Financial Services

- `POST /financial/advice` - Get personalized financial advice
- `POST /financial/chat` - Chat with the AI assistant

### Health Check

- `GET /health` - Check API health status

## Authentication

The AI service uses the same authentication tokens as the main backend API. The frontend should:

1. Authenticate with the main backend to get a token
2. Pass that same token to the AI service endpoints

```
Authorization: Bearer <your_backend_token>
```

The AI service will:
1. Validate the token with the backend
2. Use the same token to fetch user data from the backend

This approach simplifies authentication by reusing the existing tokens.

## Example Requests

### Get Financial Advice

```
POST /financial/advice
Authorization: Bearer <your_backend_token>
Content-Type: application/json

{
    "message": "What should I do with my savings?"
}
```

### Chat with AI

```
POST /financial/chat
Authorization: Bearer <your_backend_token>
Content-Type: application/json

{
    "content": "How are my investments performing?",
    "chat_history": []
}
```

## Swagger Documentation

Access the interactive API documentation at `http://localhost:8000/docs`.

## Development

- API is built with FastAPI for high performance
- Pass-through authentication leverages existing backend security
- Integration with LLMs for financial advice generation

## License

[MIT License]

## Contact

Wealth Management Team 