#!/usr/bin/env bash
# Pre-push hook for automatic linting checks

echo "🔍 Running pre-push linting checks..."
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
ERRORS=0

# Check Python linting
echo "📝 Checking Python linting..."
PYTHON_ERRORS=$(python3 -m flake8 . --select=E,F --max-line-length=120 \
    --exclude=.venv,node_modules,__pycache__,dist,build,.git,Edge/electron-app,Edge/WebUI/migrations \
    --count 2>&1 | tail -1)

if [ "$PYTHON_ERRORS" = "0" ]; then
    echo -e "${GREEN}✓ Python linting passed (0 critical errors)${NC}"
else
    echo -e "${RED}✗ Python linting failed: $PYTHON_ERRORS critical error(s)${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "📝 Checking JavaScript syntax..."
JS_FILES=$(find . -name "*.js" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/dist/*" -not -path "*/.git/*" -not -name "*.min.js" 2>/dev/null)
JS_ERRORS=0
for file in $JS_FILES; do
    if ! node --check "$file" 2>/dev/null; then
        echo -e "${RED}✗ Syntax error in: $file${NC}"
        JS_ERRORS=$((JS_ERRORS + 1))
    fi
done

if [ $JS_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ JavaScript syntax check passed${NC}"
else
    echo -e "${RED}✗ JavaScript syntax check failed: $JS_ERRORS error(s)${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All linting checks passed! Pushing code...${NC}"
    exit 0
else
    echo -e "${RED}✗ Linting checks failed${NC}"
    echo "To skip this check, use: git push --no-verify"
    exit 1
fi
