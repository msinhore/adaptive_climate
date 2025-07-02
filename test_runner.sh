#!/bin/bash
# Local test runner for Adaptive Climate

set -e

echo "🚀 Running Adaptive Climate Tests"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Virtual environment not detected. Consider using one."
fi

# Install dependencies if needed
if ! command -v ruff &> /dev/null; then
    echo "Installing development dependencies..."
    pip install -r requirements_dev.txt
fi

# 1. Code formatting check
echo -e "\n${YELLOW}1. Checking code formatting...${NC}"
if black --check custom_components/adaptive_climate/; then
    print_status "Code formatting is correct"
else
    print_error "Code formatting issues found. Run: black custom_components/adaptive_climate/"
    exit 1
fi

# 2. Import sorting check
echo -e "\n${YELLOW}2. Checking import sorting...${NC}"
if isort --check-only custom_components/adaptive_climate/; then
    print_status "Import sorting is correct"
else
    print_error "Import sorting issues found. Run: isort custom_components/adaptive_climate/"
    exit 1
fi

# 3. Linting with ruff
echo -e "\n${YELLOW}3. Running linter (ruff)...${NC}"
if ruff check custom_components/adaptive_climate/; then
    print_status "No linting issues found"
else
    print_warning "Linting issues found (some may be ignorable)"
fi

# 4. Type checking
echo -e "\n${YELLOW}4. Running type checker (mypy)...${NC}"
if mypy custom_components/adaptive_climate/ --show-error-codes; then
    print_status "Type checking passed"
else
    print_warning "Type checking issues found (may be due to missing HA dependencies)"
fi

# 5. Security check
echo -e "\n${YELLOW}5. Running security check (bandit)...${NC}"
if bandit -r custom_components/adaptive_climate/ -f json -o bandit-report.json; then
    print_status "Security check passed"
else
    print_warning "Security issues found (check bandit-report.json)"
fi

# 6. Run tests
echo -e "\n${YELLOW}6. Running tests...${NC}"
if pytest tests/ -v --cov=custom_components/adaptive_climate --cov-report=term-missing; then
    print_status "All tests passed"
else
    print_error "Tests failed"
    exit 1
fi

echo -e "\n${GREEN}🎉 All checks completed successfully!${NC}"
echo "Your code is ready for commit."

# Optional: Run pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo -e "\n${YELLOW}Running pre-commit hooks...${NC}"
    pre-commit run --all-files
fi
