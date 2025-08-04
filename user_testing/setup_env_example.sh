#!/bin/bash
# HoopHead Environment Setup Example
# ================================
# Copy this file to setup_env.sh and add your real API key

echo "🏀 HoopHead Environment Setup"
echo "============================="

# Replace 'your_ball_dont_lie_api_key_here' with your actual API key from https://balldontlie.io
export BALLDONTLIE_API_KEY="your_ball_dont_lie_api_key_here"

# Optional: Set encryption key for persistent storage (recommended for production)
# export HOOPHEAD_ENCRYPTION_KEY="your_32_character_encryption_key_"

echo "✅ Environment variables set!"
echo "🔑 API Key: ${BALLDONTLIE_API_KEY:0:8}..."

echo ""
echo "🧪 Quick Test Commands:"
echo "  python test_api_key.py          # Test your API key"
echo "  python simple_api_demo.py       # View usage patterns + live demo"
echo "  python quick_example.py         # Simple working example"
echo "  python example_usage.py         # Comprehensive examples"

echo ""
echo "🔧 To make this permanent, add to your shell profile:"
echo "  echo 'export BALLDONTLIE_API_KEY=\"your_key\"' >> ~/.zshrc"
echo "  source ~/.zshrc"

echo ""
echo "💡 Get your API key at: https://balldontlie.io" 