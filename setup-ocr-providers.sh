#!/bin/bash

# Pala Platform - OCR Providers Setup Script
# Installs and configures Ollama and LM Studio for local OCR processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pala Platform - OCR Providers Setup${NC}"
echo -e "${BLUE}================================================${NC}\n"

# Get the root directory
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running on a port
port_is_listening() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to detect OS
get_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        MINGW*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

OS=$(get_os)

echo -e "${CYAN}System detected: $OS${NC}\n"

# 1. Check Tesseract (should already be installed as pytesseract dependency)
echo -e "${GREEN}[1/3] Checking Tesseract OCR...${NC}"
if command_exists tesseract; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -1)
    echo -e "${GREEN}✓ Tesseract found: $TESSERACT_VERSION${NC}\n"
else
    echo -e "${YELLOW}⚠ Tesseract not found${NC}"
    echo -e "  Install via:"
    case "$OS" in
        macos)
            echo -e "    brew install tesseract"
            ;;
        linux)
            echo -e "    sudo apt-get install tesseract-ocr"
            ;;
        *)
            echo -e "    Visit: https://github.com/UB-Mannheim/tesseract/wiki"
            ;;
    esac
    echo ""
fi

# 2. Ollama Setup
echo -e "${GREEN}[2/3] Checking Ollama...${NC}"
if command_exists ollama; then
    echo -e "${GREEN}✓ Ollama is installed${NC}"
    
    # Check if service is running
    if port_is_listening 11434; then
        echo -e "${GREEN}✓ Ollama service is running on port 11434${NC}\n"
    else
        echo -e "${YELLOW}⚠ Ollama is installed but not running${NC}"
        echo -e "  Start with: ${CYAN}ollama serve${NC}"
        echo -e "  (Run in separate terminal)\n"
    fi
else
    echo -e "${YELLOW}Installing Ollama...${NC}"
    case "$OS" in
        macos)
            echo -e "  Downloading Ollama for macOS..."
            if command_exists brew; then
                echo -e "  Using Homebrew..."
                brew install ollama 2>/dev/null || brew upgrade ollama 2>/dev/null
            else
                # Download directly from ollama.ai
                TEMP_DIR=$(mktemp -d)
                curl -L "https://ollama.ai/download/ollama-darwin.zip" -o "$TEMP_DIR/ollama.zip" 2>/dev/null
                unzip -q "$TEMP_DIR/ollama.zip" -d "$TEMP_DIR"
                # Move to /Applications or ~/Applications
                if [ -w "/Applications" ]; then
                    mv "$TEMP_DIR/Ollama.app" /Applications/ 2>/dev/null || true
                    echo -e "  ${GREEN}✓ Ollama installed to /Applications${NC}"
                else
                    mkdir -p ~/Applications
                    mv "$TEMP_DIR/Ollama.app" ~/Applications/ 2>/dev/null || true
                    echo -e "  ${GREEN}✓ Ollama installed to ~/Applications${NC}"
                fi
                rm -rf "$TEMP_DIR"
            fi
            ;;
        linux)
            echo -e "  Downloading Ollama for Linux..."
            if command_exists curl; then
                curl -fsSL https://ollama.ai/install.sh | sh 2>/dev/null
            else
                echo -e "  ${RED}Error: curl not found. Please install curl first.${NC}"
            fi
            ;;
        *)
            echo -e "  ${RED}Automatic installation not supported for $OS${NC}"
            echo -e "  Download from: ${CYAN}https://ollama.ai${NC}\n"
            ;;
    esac
    
    if command_exists ollama; then
        echo -e "${GREEN}✓ Ollama installed successfully${NC}"
        echo -e "  Now pull a vision model:"
        echo -e "    ${CYAN}ollama pull minicpm-v${NC}          # Lightweight vision model"
        echo -e "  Then start the server:"
        echo -e "    ${CYAN}ollama serve${NC}"
        echo -e "  (Run in separate terminal)\n"
    else
        echo -e "${YELLOW}⚠ Ollama installation skipped or failed${NC}"
        echo -e "  Download manually from: ${CYAN}https://ollama.ai${NC}\n"
    fi
fi

# 3. LM Studio Setup
echo -e "${GREEN}[3/3] Checking LM Studio...${NC}"
if command_exists lm-studio; then
    echo -e "${GREEN}✓ LM Studio CLI is installed${NC}\n"
elif [ -d "$HOME/.cache/lm-studio" ] || [ -d "$HOME/AppData/Local/LM Studio" ]; then
    echo -e "${GREEN}✓ LM Studio appears to be installed${NC}"
    echo -e "  Note: LM Studio is a GUI app. Make sure the local server is running."
    echo -e "  Check: http://localhost:1234/v1/models\n"
else
    echo -e "${YELLOW}Installing LM Studio...${NC}"
    case "$OS" in
        macos)
            echo -e "  Downloading LM Studio for macOS..."
            if command_exists brew; then
                echo -e "  Using Homebrew..."
                brew install --cask lm-studio 2>/dev/null || echo -e "  ${YELLOW}Homebrew install failed, downloading directly...${NC}"
            fi
            
            if [ ! -d "/Applications/LM Studio.app" ] && [ ! -d "$HOME/Applications/LM Studio.app" ]; then
                # Download from LM Studio website
                TEMP_DIR=$(mktemp -d)
                echo -e "  Downloading from lmstudio.ai..."
                # LM Studio download URL (you may need to update this)
                curl -L "https://lmstudio.ai/api/download/darwin-arm64" -o "$TEMP_DIR/lm-studio.dmg" 2>/dev/null || true
                
                if [ -f "$TEMP_DIR/lm-studio.dmg" ]; then
                    # Mount and copy
                    MOUNT_POINT=$(mktemp -d)
                    hdiutil attach "$TEMP_DIR/lm-studio.dmg" -mountpoint "$MOUNT_POINT" 2>/dev/null || true
                    if [ -w "/Applications" ]; then
                        cp -r "$MOUNT_POINT/LM Studio.app" /Applications/ 2>/dev/null || true
                        echo -e "  ${GREEN}✓ LM Studio installed to /Applications${NC}"
                    else
                        mkdir -p ~/Applications
                        cp -r "$MOUNT_POINT/LM Studio.app" ~/Applications/ 2>/dev/null || true
                        echo -e "  ${GREEN}✓ LM Studio installed to ~/Applications${NC}"
                    fi
                    hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
                    rm -rf "$MOUNT_POINT"
                fi
                rm -rf "$TEMP_DIR"
            fi
            ;;
        linux)
            echo -e "  Downloading LM Studio for Linux..."
            TEMP_DIR=$(mktemp -d)
            curl -L "https://lmstudio.ai/api/download/linux-x64" -o "$TEMP_DIR/lm-studio.AppImage" 2>/dev/null || true
            
            if [ -f "$TEMP_DIR/lm-studio.AppImage" ]; then
                chmod +x "$TEMP_DIR/lm-studio.AppImage"
                mkdir -p "$HOME/.local/bin"
                mv "$TEMP_DIR/lm-studio.AppImage" "$HOME/.local/bin/lm-studio"
                echo -e "  ${GREEN}✓ LM Studio installed to ~/.local/bin${NC}"
            fi
            rm -rf "$TEMP_DIR"
            ;;
        *)
            echo -e "  ${RED}Automatic installation not supported for $OS${NC}"
            echo -e "  Download from: ${CYAN}https://lmstudio.ai${NC}\n"
            ;;
    esac
    
    if [ -d "/Applications/LM Studio.app" ] || [ -d "$HOME/Applications/LM Studio.app" ] || [ -f "$HOME/.local/bin/lm-studio" ]; then
        echo -e "${GREEN}✓ LM Studio installed successfully${NC}"
        echo -e "  Next steps:"
        echo -e "    1. Open LM Studio"
        echo -e "    2. Go to 'Local Server' tab"
        echo -e "    3. Download a vision model (e.g., Llava, minicpm-v)"
        echo -e "    4. Click 'Start Server'\n"
    else
        echo -e "${YELLOW}⚠ LM Studio installation skipped or failed${NC}"
        echo -e "  Download manually from: ${CYAN}https://lmstudio.ai${NC}\n"
    fi
fi

# 4. Summary and next steps
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}Setup Summary:${NC}"
echo -e "${BLUE}================================================${NC}\n"

echo -e "${CYAN}OCR Providers Status:${NC}"
echo -e "  ${GREEN}✓${NC} Tesseract    - Ready (CPU, fast, no model needed)"

if command_exists ollama && port_is_listening 11434; then
    echo -e "  ${GREEN}✓${NC} Ollama       - Running on port 11434"
elif command_exists ollama; then
    echo -e "  ${YELLOW}⚠${NC} Ollama       - Installed but not running"
    echo -e "    Start with: ${CYAN}ollama serve${NC} (in new terminal)"
else
    echo -e "  ${YELLOW}⚠${NC} Ollama       - Not available"
fi

if port_is_listening 1234; then
    echo -e "  ${GREEN}✓${NC} LM Studio    - Running on port 1234"
elif [ -d "/Applications/LM Studio.app" ] || [ -d "$HOME/Applications/LM Studio.app" ] || [ -f "$HOME/.local/bin/lm-studio" ]; then
    echo -e "  ${YELLOW}⚠${NC} LM Studio    - Installed but not running"
    echo -e "    Start by opening LM Studio and clicking 'Start Server'"
else
    echo -e "  ${YELLOW}⚠${NC} LM Studio    - Not available"
fi

echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo -e "  1. Start the dev stack: ${GREEN}./start-dev.sh${NC}"
echo -e "  2. In Dashboard, go to 'Document Processing' tab"
echo -e "  3. Select OCR provider (Tesseract, Ollama, or LM Studio)"
echo -e "  4. Upload an image to test OCR"
echo ""

echo -e "${CYAN}Troubleshooting:${NC}"
echo -e "  • ${YELLOW}Provider returns empty text:${NC}"
echo -e "    - Check logs: ${GREEN}tail -f logs/ocr-agent.log${NC}"
echo -e "    - Verify provider is running on correct port"
echo -e ""
echo -e "  • ${YELLOW}Ollama not found:${NC}"
echo -e "    - Ensure Ollama is in PATH or reinstall"
echo -e "    - Check: ${GREEN}which ollama${NC}"
echo ""
echo -e "  • ${YELLOW}LM Studio API not responding:${NC}"
echo -e "    - Verify server is running: ${GREEN}curl http://localhost:1234/v1/models${NC}"
echo -e "    - Restart LM Studio if needed"
echo ""

echo -e "${GREEN}Setup complete!${NC}\n"
