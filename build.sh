#!/bin/bash
# Build CAN Analyzer package (macOS / Linux)
# Usage: ./build.sh

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}CAN Analyzer - Build${NC}"
echo "================================"

# Use venv if present
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating venv...${NC}"
    source venv/bin/activate
fi

# Install build dependencies
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements-dev.txt
fi

# Clean previous build
echo -e "${YELLOW}Cleaning previous build...${NC}"
rm -rf build dist

# Build based on platform
if [ "$(uname)" = "Darwin" ]; then
    # macOS: Use py2app
    echo -e "${GREEN}Building for macOS with py2app...${NC}"
    
    if [ -f "icon.icns" ]; then
        echo -e "${YELLOW}Using icon: icon.icns${NC}"
    else
        echo -e "${YELLOW}No icon found. Place icon.icns in project root to add an icon.${NC}"
    fi
    
    python setup.py py2app
    
    echo -e "${GREEN}Done. Output: dist/CAN Analyzer.app${NC}"
    echo -e "${YELLOW}To run: open 'dist/CAN Analyzer.app'${NC}"
else
    # Linux: Use PyInstaller
    echo -e "${GREEN}Building for Linux with PyInstaller...${NC}"
    
    if [ -f "icon.ico" ]; then
        echo -e "${YELLOW}Using icon: icon.ico${NC}"
    else
        echo -e "${YELLOW}No icon found. Place icon.ico in project root to add an icon.${NC}"
    fi
    
    pyinstaller --clean --noconfirm can_analyzer.spec
    
    echo -e "${GREEN}Done. Output: dist/CAN Analyzer/${NC}"
    echo -e "${YELLOW}To run: ./dist/CAN Analyzer/CAN Analyzer${NC}"
fi
