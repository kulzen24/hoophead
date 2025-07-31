# HoopHead 🏀

A Model Context Protocol (MCP) application that provides intelligent access to basketball statistics from Basketball Reference. Ask questions in natural language and get accurate, contextual answers about NBA players, teams, and statistics.

## 🎯 Features

- **Natural Language Queries**: Ask basketball questions in plain English
- **Real-time Data**: Live data from Basketball Reference
- **Smart Responses**: AI-powered contextual answers with statistical insights
- **Modern UI**: Clean, responsive NextJS frontend
- **MCP Integration**: Seamless integration with Claude for enhanced capabilities

## 🏗️ Architecture

- **Frontend**: NextJS 14 with TypeScript and Tailwind CSS
- **Backend**: Python FastAPI with async request handling
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for performance optimization
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

# Basketball Reference
BASKETBALL_REFERENCE_BASE_URL=https://www.basketball-reference.com
SCRAPING_DELAY=1.0
MAX_RETRIES=3

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Usage Examples

Once the application is running, you can ask questions like:

- "What are LeBron James' career stats?"
- "How did the Lakers perform last season?"
- "Compare Stephen Curry and Magic Johnson's three-point shooting"
- "Show me the top scorers from the 2023 season"

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Basketball Reference for providing comprehensive basketball statistics
- The MCP community for the Model Context Protocol specification
- FastAPI and NextJS communities for excellent frameworks

## 🐛 Troubleshooting

### Common Issues

1. **Docker build fails**: Ensure Docker has enough memory allocated (4GB+)
2. **Database connection errors**: Check PostgreSQL is running and credentials are correct
3. **Frontend not loading**: Verify the backend is running on port 8000
4. **Rate limiting from Basketball Reference**: Implement delays between requests

### Getting Help

- Check the [Issues](https://github.com/your-repo/hoophead/issues) page
- Review the API documentation at http://localhost:8000/docs
- Check Docker container logs: `docker-compose logs -f`

## 🗺️ Roadmap

- [ ] Advanced statistical analysis
- [ ] Player comparison visualizations
- [ ] Historical trend analysis
- [ ] Mobile app development
- [ ] Integration with additional sports data sources
- [ ] Machine learning for query intent recognition 