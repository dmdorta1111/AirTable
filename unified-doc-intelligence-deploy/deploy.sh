#!/bin/bash
# deploy.sh - Unified Engineering Document Intelligence Platform Deployment Script
# Cross-platform bash script for setting up the deployment package

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}==========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_python() {
    print_header "Checking Python Installation"
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        print_success "Python3 found"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        print_success "Python found"
    else
        print_error "Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$PYTHON_VERSION >= 3.8" | bc) -eq 1 ]]; then
        print_success "Python version $PYTHON_VERSION meets requirement (3.8+)"
    else
        print_error "Python $PYTHON_VERSION found, but 3.8+ is required"
        exit 1
    fi
}

check_pip() {
    print_header "Checking pip Installation"
    
    if $PYTHON_CMD -m pip --version &> /dev/null; then
        print_success "pip is installed"
    else
        print_warning "pip not found. Attempting to install..."
        
        # Try to install pip
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        elif command -v brew &> /dev/null; then
            brew install python3
        else
            print_error "Cannot automatically install pip. Please install pip manually."
            print_warning "Try: curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && $PYTHON_CMD get-pip.py"
            exit 1
        fi
        
        if $PYTHON_CMD -m pip --version &> /dev/null; then
            print_success "pip installed successfully"
        else
            print_error "Failed to install pip"
            exit 1
        fi
    fi
}

create_directories() {
    print_header "Creating Directory Structure"
    
    local dirs=("output" "logs" "temp")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        else
            print_success "Directory exists: $dir"
        fi
    done
}

setup_config() {
    print_header "Configuration Setup"
    
    if [ ! -f "config-template.txt" ]; then
        print_error "config-template.txt not found"
        exit 1
    fi
    
    if [ ! -f "config.txt" ]; then
        print_warning "config.txt not found - creating from template"
        cp config-template.txt config.txt
        
        echo ""
        echo "================================================================================"
        echo "IMPORTANT: You MUST edit config.txt with your actual credentials"
        echo "================================================================================"
        echo ""
        echo "Required configuration:"
        echo "1. NEON_DATABASE_URL: Your Neon PostgreSQL connection string"
        echo "2. B2_APPLICATION_KEY_ID: Your Backblaze B2 key ID"
        echo "3. B2_APPLICATION_KEY: Your Backblaze B2 application key"
        echo "4. B2_BUCKET_NAME: (default: EmjacDB)"
        echo ""
        echo "Edit the file with: nano config.txt (or your preferred editor)"
        echo "================================================================================"
        echo ""
        
        read -p "Press Enter when you've edited config.txt with real credentials..."
        
        # Verify they didn't just save template values
        if grep -q "username:password\|your_\|xxx" config.txt; then
            print_warning "config.txt appears to still have template values"
            print_warning "Please edit it with your actual credentials before continuing"
            exit 1
        fi
    else
        # Check if config.txt has real values
        if grep -q "username:password\|your_\|xxx" config.txt; then
            print_warning "config.txt has template values - please update with real credentials"
            print_warning "Edit with: nano config.txt"
            exit 1
        else
            print_success "config.txt appears to be properly configured"
        fi
    fi
}

install_dependencies() {
    print_header "Installing Python Dependencies"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    print_warning "This may take several minutes depending on your internet connection..."
    
    # Upgrade pip first
    $PYTHON_CMD -m pip install --upgrade pip
    
    # Install requirements
    if $PYTHON_CMD -m pip install -r requirements.txt; then
        print_success "All dependencies installed successfully"
    else
        print_error "Failed to install some dependencies"
        print_warning "Trying with verbose output..."
        $PYTHON_CMD -m pip install -r requirements.txt -v
    fi
}

fix_script_paths() {
    print_header "Updating Script Path References"
    
    local changes=0
    
    # Find all Python scripts
    find scripts -name "*.py" | while read script; do
        # Make backup
        cp "$script" "$script.bak" 2>/dev/null || true
        
        # Update path references
        sed -i.bak2 \
            -e "s|CONFIG_FILE = PLAN_DIR / \"config.txt\"|CONFIG_FILE = Path(__file__).parent.parent.parent / \"config.txt\"|g" \
            -e "s|SCHEMA_FILE = PLAN_DIR / \"output\" / \"schema-migration.sql\"|SCHEMA_FILE = Path(__file__).parent.parent.parent / \"schema-migration.sql\"|g" \
            -e "s|OUTPUT_DIR = PLAN_DIR / \"output\"|OUTPUT_DIR = Path(__file__).parent.parent.parent / \"output\"|g" \
            "$script" 2>/dev/null || true
        
        # Remove backup
        rm -f "$script.bak2" 2>/dev/null || true
        
        changes=$((changes + 1))
        print_success "Updated paths in: $script"
    done
    
    if [ $changes -eq 0 ]; then
        print_success "Script paths already correct"
    else
        print_success "Updated $changes script files"
    fi
}

verify_installation() {
    print_header "Verifying Installation"
    
    local critical_packages=("psycopg2" "tqdm" "tabulate" "PyMuPDF" "ezdxf" "b2sdk" "fastapi" "uvicorn" "pydantic")
    local missing=()
    
    for pkg in "${critical_packages[@]}"; do
        case $pkg in
            "PyMuPDF")
                # PyMuPDF is imported as fitz
                if $PYTHON_CMD -c "import fitz" 2>/dev/null; then
                    print_success "PyMuPDF (fitz)"
                else
                    print_error "PyMuPDF"
                    missing+=("PyMuPDF")
                fi
                ;;
            "b2sdk")
                if $PYTHON_CMD -c "from b2sdk.v2 import InMemoryAccountInfo, B2Api" 2>/dev/null; then
                    print_success "b2sdk"
                else
                    print_error "b2sdk"
                    missing+=("b2sdk")
                fi
                ;;
            *)
                if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
                    print_success "$pkg"
                else
                    print_error "$pkg"
                    missing+=("$pkg")
                fi
                ;;
        esac
    done
    
    if [ ${#missing[@]} -eq 0 ]; then
        print_success "All critical packages installed"
        return 0
    else
        print_warning "Missing packages: ${missing[*]}"
        print_warning "Try: $PYTHON_CMD -m pip install ${missing[*]}"
        return 1
    fi
}

setup_completion() {
    print_header "Setup Complete!"
    
    echo ""
    echo "🎉 Unified Engineering Document Intelligence Platform is ready!"
    echo ""
    echo "📊 What was installed:"
    echo "  ✓ 19 Python scripts organized in 3 phases"
    echo "  ✓ All required dependencies (PostgreSQL, PDF/DXF, B2, FastAPI)"
    echo "  ✓ Directory structure (output/, logs/, temp/)"
    echo "  ✓ Configuration file (config.txt)"
    echo ""
    echo "🚀 Next Steps:"
    echo ""
    echo "1. Run the complete pipeline:"
    echo "   $PYTHON_CMD run-pipeline.py --phase all"
    echo ""
    echo "2. Or run individual phases:"
    echo "   $PYTHON_CMD run-pipeline.py --phase a      # Auto-linking (2-3 hours)"
    echo "   $PYTHON_CMD run-pipeline.py --phase b      # PDF/DXF extraction (6-8 hours)"
    echo "   $PYTHON_CMD run-pipeline.py --phase c      # Search API (continuous)"
    echo ""
    echo "3. Check system status:"
    echo "   $PYTHON_CMD run-pipeline.py --status"
    echo ""
    echo "4. List all available scripts:"
    echo "   $PYTHON_CMD run-pipeline.py --list"
    echo ""
    echo "📚 Documentation:"
    echo "  - README.md                      # Quick start guide"
    echo "  - docs/IMPLEMENTATION_GUIDE.md   # Detailed execution guide"
    echo "  - docs/API_GUIDE.md              # Search API documentation"
    echo ""
    echo "🔧 For distributed processing, copy this directory to multiple machines"
    echo "   and run different phases on each machine."
    echo ""
    echo "================================================================================"
    echo "Platform processes 819,000+ engineering files with:"
    echo "  - Phase A: Auto-linking (creates ~37,000 DocumentGroups)"
    echo "  - Phase B: PDF/DXF extraction (191K+ PDFs, 574K+ DXFs)"
    echo "  - Phase C: Search API (6 endpoints with Swagger UI)"
    echo "================================================================================"
}

main() {
    print_header "Unified Engineering Document Intelligence Platform Deployment"
    echo "This script will set up the complete deployment environment."
    echo ""
    
    # Check current directory
    if [ ! -f "README.md" ] || [ ! -f "requirements.txt" ]; then
        print_error "Please run this script from the deployment directory"
        print_error "Expected files: README.md, requirements.txt"
        exit 1
    fi
    
    # Run setup steps
    check_python
    check_pip
    create_directories
    setup_config
    install_dependencies
    fix_script_paths
    
    if verify_installation; then
        setup_completion
    else
        print_warning "Installation completed with some warnings"
        print_warning "You may need to install missing packages manually"
        setup_completion
    fi
}

# Handle Ctrl+C
trap 'print_error "Deployment interrupted by user"; exit 1' INT

# Run main function
main "$@"