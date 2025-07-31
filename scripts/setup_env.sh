#!/bin/bash

# SportsMind Development Environment Setup Script
echo "🏆 SportsMind Development Environment Setup"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Set up Python virtual environment
echo "📦 Setting up Python virtual environment..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📚 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
else
    echo "❌ Failed to install Python dependencies"
    echo "⚠️  Some packages may require system dependencies or may not be compatible with your Python version"
    echo "   You can still test the Ball Don't Lie API with basic dependencies by running:"
    echo "   pip install aiohttp requests python-dotenv pydantic pydantic-settings"
fi

cd ..

# Set up environment file
echo "🔧 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo ""
    echo "🔑 IMPORTANT: Add your Ball Don't Lie API key to the .env file:"
    echo "   BALL_DONT_LIE_API_KEY=your_api_key_here"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Set up frontend (basic check)
echo "🌐 Checking frontend setup..."
cd frontend
if [ ! -d "node_modules" ]; then
    if command -v npm &> /dev/null; then
        echo "📦 Installing Node.js dependencies..."
        npm install
        echo "✅ Node.js dependencies installed"
    else
        echo "⚠️  npm not found. Please install Node.js to set up the frontend"
    fi
else
    echo "✅ Node.js dependencies already installed"
fi

cd ..

echo ""
echo "🎉 Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Get your Ball Don't Lie API key from https://balldontlie.io"
echo "2. Add it to .env file: BALL_DONT_LIE_API_KEY=your_api_key_here"
echo "3. Test the API: python scripts/test_ball_dont_lie_api.py"
echo "4. Start development with Task 2 in TaskMaster"
echo ""
echo "🚀 Ready to build SportsMind - the multi-sport MCP platform!" 