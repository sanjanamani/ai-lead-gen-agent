#!/bin/bash
# Setup script for Convexia CRM Agent

echo "🚀 Setting up Convexia CRM Agent..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )(.+)')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version"
echo ""

# Create virtual environment (optional but recommended)
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate 2>/dev/null
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
echo "⚙️  Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - GOOGLE_API_KEY (get from: https://aistudio.google.com/app/apikey)"
    echo "   - SERPAPI_KEY (get from: https://serpapi.com/manage-api-key)"
else
    echo "⚠️  .env file already exists (not overwriting)"
fi
echo ""

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/cache data/output data/logs
echo "✅ Data directories created"
echo ""

# Test imports
echo "🧪 Testing installation..."
python3 -c "
import sys
try:
    from agent import ConvexiaCRMAgent
    from config.settings import config
    print('✅ All imports successful')
    print(f'✅ Configuration loaded')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"
echo ""

echo "="*80
echo "✅ SETUP COMPLETE!"
echo "="*80
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Run example: python main.py"
echo "  3. Check README.md for more information"
echo ""
echo "Free API keys:"
echo "  • Google Gemini: https://aistudio.google.com/app/apikey"
echo "  • SerpAPI: https://serpapi.com/manage-api-key"
echo ""
echo "Happy lead generation! 🎯"
