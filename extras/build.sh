#!/bin/bash
# Build CAN Analyzer package (macOS / Linux)
# Run from project root: ./extras/build.sh

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${GREEN}CAN Analyzer - Build${NC}"
echo "================================"

# Create and use venv so build always runs with isolated deps
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating venv...${NC}"
    python3 -m venv venv
fi
echo -e "${YELLOW}Activating venv...${NC}"
source venv/bin/activate

# Validate and install dependencies (runtime + build tools for this platform)
NEED_INSTALL=""
if [ "$(uname)" = "Darwin" ]; then
    python -c "import py2app" 2>/dev/null || NEED_INSTALL=1
else
    python -c "import PyInstaller" 2>/dev/null || NEED_INSTALL=1
fi
python -c "import PyQt6, can, serial" 2>/dev/null || NEED_INSTALL=1
if [ -n "$NEED_INSTALL" ]; then
    echo -e "${YELLOW}Installing dependencies (requirements-dev.txt)...${NC}"
    pip install -r requirements-dev.txt
fi

# Regenerate icons from source PNG if present (unified with create_icon.sh)
ICON_SOURCE="icon.png"
if [ -f "$ICON_SOURCE" ]; then
    echo -e "${YELLOW}Regenerating icons from $ICON_SOURCE...${NC}"
    "$SCRIPT_DIR/create_icon.sh" "$ICON_SOURCE"
else
    if [ ! -f "icon.icns" ] && [ ! -f "icon.ico" ]; then
        echo -e "${YELLOW}Tip: put icon.png in project root and run ./extras/build.sh to auto-generate icon.icns/icon.ico${NC}"
    fi
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
