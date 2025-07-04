# Archelyst Python Backend

High-performance Python backend for Archelyst.ai - AI-enhanced financial data and analytics API

## 🚀 Overview

Archelyst Backend is a sophisticated financial data and analytics API built with FastAPI that provides:
- **Real-time market data** from multiple providers with intelligent failover
- **AI-powered financial analysis** using OpenAI GPT-4, Claude, and other providers
- **Advanced technical analysis** with 50+ indicators via TA-Lib
- **Portfolio optimization** and risk analytics
- **Knowledge graph integration** for entity relationships
- **Production-ready architecture** supporting 1000+ concurrent users

## 🏗️ Architecture

```
├── app/
│   ├── api/v1/endpoints/     # REST API endpoints
│   ├── core/                 # Configuration and security
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── data_providers/  # Market data providers
│   │   └── ai_providers/    # AI service providers
│   └── workers/             # Background tasks
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
└── docker-compose.yml      # Container orchestration
```

## 🛠️ Technology Stack

- **FastAPI** - High-performance async web framework
- **PostgreSQL** - Primary database with async SQLAlchemy
- **Redis** - Caching and background task queue
- **Neo4j** - Knowledge graph for entity relationships
- **Celery** - Distributed task processing
- **Docker** - Containerization and deployment

## 📊 Data Providers

- **Financial Modeling Prep** - Primary market data source
- **Yahoo Finance** - Free tier and backup data
- **Alpha Vantage** - Alternative data provider
- **Hot-swappable architecture** - Easy provider integration

## 🤖 AI Integration

- **OpenAI GPT-4** - Market analysis and insights
- **Anthropic Claude** - Alternative AI analysis
- **Google AI** - Specialized tasks
- **Provider failover** - Automatic switching on failures

## 🔧 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Redis
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dexjgraf/archelyst-backend.git
cd archelyst-backend
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. Start with Docker Compose:
```bash
docker-compose up -d
```

4. Or run locally:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🚦 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔑 Core API Endpoints

### Market Data
- `GET /api/v1/securities/quote/{symbol}` - Real-time quotes
- `GET /api/v1/securities/profile/{symbol}` - Company profiles
- `POST /api/v1/securities/search` - Security search
- `GET /api/v1/market/overview` - Market overview

### AI Services
- `GET /api/v1/ai/market-insights` - Daily market analysis
- `GET /api/v1/ai/stock-analysis/{symbol}` - Individual stock analysis
- `POST /api/v1/ai/screen` - AI-powered stock screening

### Technical Analysis
- `GET /api/v1/technical/{symbol}/indicators` - Technical indicators
- `GET /api/v1/technical/{symbol}/patterns` - Chart patterns
- `GET /api/v1/technical/{symbol}/levels` - Support/resistance levels

### Portfolio Analytics
- `POST /api/v1/portfolio/analyze` - Portfolio metrics
- `POST /api/v1/portfolio/optimize` - Portfolio optimization
- `POST /api/v1/portfolio/risk` - Risk analysis

## 📈 Performance

- **Sub-2-second response times** for all endpoints
- **99.9% uptime** with proper deployment
- **1000+ concurrent users** supported
- **Intelligent caching** with Redis
- **Automatic failover** between data providers

## 🔒 Security

- JWT token authentication
- API key management
- Rate limiting
- Input validation
- SQL injection protection
- CORS configuration

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/dexjgraf/archelyst-backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dexjgraf/archelyst-backend/discussions)
- **Email**: support@archelyst.ai

---

**Built with ❤️ for the financial technology community**