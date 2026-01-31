#!/bin/bash
# CAN Analyzer - Run script (macOS / Linux)
# Automates venv creation and dependency installation

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}CAN Analyzer${NC}"
echo "================================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo -e "${RED}Error creating virtual environment!${NC}"
        exit 1
    fi

    echo -e "${GREEN}Virtual environment created successfully!${NC}"
fi

# Activate the virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import can" 2>/dev/null; then
    echo -e "${YELLOW}Installing runtime dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo -e "${RED}Error installing dependencies!${NC}"
        exit 1
    fi

    echo -e "${GREEN}Dependencies installed successfully!${NC}"
fi

# Run the application
echo -e "${GREEN}Starting CAN Analyzer...${NC}"
python can_analyzer_qt.py

# Deactivate virtual environment on exit
deactivate
