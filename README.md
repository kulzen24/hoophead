# HoopHead 🏀

A Model Context Protocol (MCP) application that provides intelligent access to multi-sport statistics from Ball Don't Lie API. Ask questions in natural language and get accurate, contextual answers about NBA, NFL, MLB, NHL, and EPL players, teams, and statistics with enterprise-grade authentication and caching.

## 🎯 Features

- **Multi-Sport Support**: NBA, NFL, MLB, NHL, and EPL statistics from Ball Don't Lie API
- **Natural Language Queries**: Ask sports questions in plain English
- **Enterprise Authentication**: Tiered API key management with secure storage and rate limiting
- **Smart Caching**: Redis-powered multi-layered caching with sport-specific TTL strategies
- **Real-time Data**: Live sports data with intelligent error handling and retry logic
- **Smart Responses**: AI-powered contextual answers with statistical insights
- **Modern UI**: Clean, responsive NextJS frontend
- **MCP Integration**: Seamless integration with Claude for enhanced capabilities

## 🏗️ Architecture

- **Frontend**: NextJS 14 with TypeScript and Tailwind CSS
- **Backend**: Python FastAPI with async request handling
- **Database**: PostgreSQL with SQLAlchemy ORM  
- **Authentication**: Enterprise-grade API key management with Fernet encryption
- **Caching**: Redis multi-layered caching with sport-specific strategies
- **External API**: Ball Don't Lie API for multi-sport statistics
- **MCP Server**: Custom MCP implementation for Claude integration
- **Containerization**: Docker and Docker Compose for development

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hoophead
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development (without Docker)

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn src.main:app --reload --port 8000
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis locally
   # Update backend/config/settings.py with your local database URLs
   ```

## 📁 Project Structure

```
hoophead/
├── backend/                 # Python FastAPI backend
│   ├── src/
│   │   ├── adapters/       # External interfaces
│   │   │   ├── controllers/    # HTTP controllers
│   │   │   ├── repositories/   # Data repositories
│   │   │   └── external/       # External service adapters
│   │   ├── domain/         # Business logic
│   │   │   ├── models/         # Domain models
│   │   │   └── services/       # Business services
│   │   └── infrastructure/ # Technical implementation
│   ├── config/             # Configuration
│   ├── tests/              # Backend tests
│   └── requirements.txt
├── frontend/               # NextJS frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Next.js pages
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── utils/          # Utility functions
│   ├── public/             # Static assets
│   └── package.json
├── docker/                 # Docker configurations
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── docker-compose.yml      # Development environment
```

## 🛠️ Development

### Code Quality

The project uses strict code quality tools:

**Backend (Python)**
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking
- pytest for testing

**Frontend (TypeScript)**
- ESLint for linting
- Prettier for code formatting
- TypeScript for type safety

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Formatting

```bash
# Backend
cd backend
black src/
isort src/
flake8 src/

# Frontend
cd frontend
npm run lint
npx prettier --write src/
```

## 🌐 API Documentation

The FastAPI backend provides interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://hoophead:password@localhost:5432/hoophead

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
SECRET_KEY=your-secret-key-here
DEBUG=true
ENVIRONMENT=development

# Ball Don't Lie API Authentication
BALLDONTLIE_API_KEY=your-ball-dont-lie-api-key
HOOPHEAD_ENCRYPTION_KEY=your-32-character-encryption-key
HOOPHEAD_API_KEYS=[{"key": "backup-key", "tier": "all-star", "label": "Backup"}]

# Ball Don't Lie API Configuration
API_REQUEST_DELAY=0.6
MAX_RETRIES=3
CACHE_TTL=3600
API_USER_AGENT=HoopHead/0.1.0

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🔐 Authentication System

HoopHead features an enterprise-grade authentication system with tiered access management:

### API Tiers

| Tier       | Requests/Hour | Requests/Minute | Concurrent | Price | Features |
|------------|---------------|-----------------|------------|-------|----------|
| **Free**   | 300           | 5               | 1          | $0    | Teams, players, games |
| **ALL-STAR**| 3,600        | 60              | 2          | $9.99 | + Player stats, injuries |
| **GOAT**   | 36,000        | 600             | 5          | $39.99| + Box scores, standings, odds |
| **Enterprise**| 36,000*    | 600*            | 10         | Custom| + Bulk export |

*Matching Ball Don't Lie API actual pricing. Enterprise tier uses GOAT limits until custom plans available.*

### Key Features

- **Secure Storage**: API keys encrypted with Fernet (AES 128)
- **Rate Limiting**: Automatic tier-based enforcement 
- **Usage Tracking**: Detailed analytics per API key
- **Multi-Key Support**: Manage and rotate multiple keys
- **Dynamic Switching**: Change API keys without restart

For detailed authentication documentation, see [backend/docs/AUTHENTICATION.md](backend/docs/AUTHENTICATION.md).

## 📊 Usage Examples

Once the application is running, you can ask questions about multiple sports:

**Basketball (NBA)**
- "What are LeBron James' career stats?"
- "How did the Lakers perform last season?"
- "Compare Stephen Curry and Magic Johnson's three-point shooting"

**Football (NFL)**  
- "Show me Tom Brady's passing statistics"
- "How many touchdowns did the Chiefs score this season?"

**Baseball (MLB)**
- "What's Aaron Judge's batting average?"
- "Compare pitching stats between teams"

**Hockey (NHL)**
- "Show me Connor McDavid's assists"
- "Which team has the best power play?"

**Soccer (EPL)**
- "Display Manchester United's goal statistics"
- "Compare Premier League top scorers"

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Ball Don't Lie API for providing comprehensive multi-sport statistics
- The MCP community for the Model Context Protocol specification
- FastAPI and NextJS communities for excellent frameworks
- Redis community for high-performance caching solutions

## 🐛 Troubleshooting

### Common Issues

1. **Docker build fails**: Ensure Docker has enough memory allocated (4GB+)
2. **Database connection errors**: Check PostgreSQL is running and credentials are correct
3. **Frontend not loading**: Verify the backend is running on port 8000
4. **Authentication errors**: 
   - Ensure `BALLDONTLIE_API_KEY` is set in environment variables
   - Check API key tier limits with `get_usage_stats()`
   - Verify encryption key format for secure storage
5. **Rate limiting**: API requests automatically throttled based on tier limits
6. **Redis connection issues**: Ensure Redis is running for caching functionality

### Getting Help

- Check the [Issues](https://github.com/your-repo/hoophead/issues) page
- Review the API documentation at http://localhost:8000/docs
- Check Docker container logs: `docker-compose logs -f`

## 🗺️ Roadmap

### ✅ Completed
- [x] Multi-sport API integration (NBA, NFL, MLB, NHL, EPL)
- [x] Enterprise authentication with tiered access management
- [x] Redis-powered multi-layered caching system
- [x] Comprehensive error handling and retry logic
- [x] Secure API key storage and rotation

### 🚧 In Progress  
- [ ] Advanced statistical analysis and insights
- [ ] Player comparison visualizations
- [ ] Historical trend analysis

### 📋 Planned
- [ ] Mobile app development
- [ ] Real-time data streaming
- [ ] Machine learning for query intent recognition
- [ ] Advanced caching strategies with predictive prefetching
- [ ] API usage analytics dashboard 