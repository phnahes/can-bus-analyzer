#!/bin/bash
# Create app icons from a PNG source (icon.icns for macOS, icon.ico for Linux).
# Run from project root: ./extras/create_icon.sh <source.png>
# Icons are written to the project root.

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No source PNG provided${NC}"
    echo "Usage: ./extras/create_icon.sh <source.png>"
    echo "Example: ./extras/create_icon.sh icon.png"
    exit 1
fi

SOURCE_PNG="$1"

if [ ! -f "$SOURCE_PNG" ]; then
    echo -e "${RED}Error: File not found: $SOURCE_PNG${NC}"
    exit 1
fi

echo -e "${GREEN}Creating app icons from: $SOURCE_PNG${NC}"
echo "================================"

# Check if Pillow is installed (needed for .ico, and for .icns fallback)
if ! python3 -c "import PIL" 2>/dev/null; then
    echo -e "${YELLOW}Installing Pillow...${NC}"
    pip install Pillow
fi

CREATED=""

# Create .icns for macOS (sips + iconutil are macOS-only)
if [ "$(uname)" = "Darwin" ]; then
    echo -e "${YELLOW}Creating icon.icns (macOS)...${NC}"
    mkdir -p icon.iconset

    sips -z 16 16     "$SOURCE_PNG" --out icon.iconset/icon_16x16.png
    sips -z 32 32     "$SOURCE_PNG" --out icon.iconset/icon_16x16@2x.png
    sips -z 32 32     "$SOURCE_PNG" --out icon.iconset/icon_32x32.png
    sips -z 64 64     "$SOURCE_PNG" --out icon.iconset/icon_32x32@2x.png
    sips -z 128 128   "$SOURCE_PNG" --out icon.iconset/icon_128x128.png
    sips -z 256 256   "$SOURCE_PNG" --out icon.iconset/icon_128x128@2x.png
    sips -z 256 256   "$SOURCE_PNG" --out icon.iconset/icon_256x256.png
    sips -z 512 512   "$SOURCE_PNG" --out icon.iconset/icon_256x256@2x.png
    sips -z 512 512   "$SOURCE_PNG" --out icon.iconset/icon_512x512.png
    sips -z 1024 1024 "$SOURCE_PNG" --out icon.iconset/icon_512x512@2x.png

    iconutil -c icns icon.iconset -o icon.icns
    rm -rf icon.iconset

    echo -e "${GREEN}✓ icon.icns created${NC}"
    CREATED="icon.icns "
fi

# Create .ico for Linux (Pillow works on macOS and Linux)
echo -e "${YELLOW}Creating icon.ico (Linux / PyInstaller)...${NC}"
python3 << EOF
from PIL import Image

img = Image.open("$SOURCE_PNG").convert('RGBA')
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save('icon.ico', format='ICO', sizes=sizes)
print("✓ icon.ico created")
EOF
CREATED="${CREATED}icon.ico"

echo ""
echo -e "${GREEN}Done! Icons created:${NC}"
ls -lh $CREATED

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review the icons (open the file(s) above)"
echo "2. Run ./extras/build.sh to rebuild the app with new icons"
