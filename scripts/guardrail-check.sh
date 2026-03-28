#!/bin/bash
# Guardrail Check — runs on every commit to ensure we don't dilute safety rules.
#
# Checks:
# 1. Every HTML page has a medical disclaimer
# 2. No HTML page uses words that sound like medical advice
# 3. API/chatbot code has guardrail patterns
# 4. Every experiment report has a limitations section
#
# Run manually: bash scripts/guardrail-check.sh
# Or install as pre-commit hook: cp scripts/guardrail-check.sh .git/hooks/pre-commit

set -e
FAIL=0
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "=== HD Research Hub Guardrail Check ==="
echo ""

# 1. Every HTML page must have a medical disclaimer
echo "Checking HTML pages for medical disclaimers..."
for f in $(find . -name "*.html" -not -path "./node_modules/*" -not -path "./.git/*"); do
  if ! grep -qi "not medical advice\|not a medical\|consult.*healthcare\|not a doctor" "$f"; then
    echo -e "  ${RED}FAIL${NC}: $f — missing medical disclaimer"
    FAIL=1
  else
    echo -e "  ${GREEN}OK${NC}: $f"
  fi
done
echo ""

# 2. No HTML page should have language that sounds like we're recommending treatment
echo "Checking for medical advice language..."
ADVICE_PATTERNS="you should take|we recommend taking|this will cure|proven to treat|guaranteed to|take this drug|start taking|stop taking your"
for f in $(find . -name "*.html" -not -path "./node_modules/*" -not -path "./.git/*"); do
  matches=$(grep -inE "$ADVICE_PATTERNS" "$f" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    echo -e "  ${RED}FAIL${NC}: $f — contains medical advice language:"
    echo "$matches" | head -3
    FAIL=1
  fi
done

# Skip api/chat.py system prompt (contains examples of what NOT to say)
for f in $(find . -name "*.py" -path "*/api/*"); do
  matches=$(grep -inE "$ADVICE_PATTERNS" "$f" 2>/dev/null | grep -v "NEVER\|Never say\|SYSTEM_PROMPT\|MEDICAL_ADVICE" || true)
  if [ -n "$matches" ]; then
    echo -e "  ${RED}FAIL${NC}: $f — contains medical advice language:"
    echo "$matches" | head -3
    FAIL=1
  fi
done
echo ""

# 3. Chatbot API must have guardrails
echo "Checking chatbot guardrails..."
if [ -f "api/chat.py" ]; then
  if ! grep -q "MEDICAL_ADVICE_PATTERNS\|MEDICAL_REDIRECT" api/chat.py; then
    echo -e "  ${RED}FAIL${NC}: api/chat.py — missing input filter guardrails"
    FAIL=1
  else
    echo -e "  ${GREEN}OK${NC}: api/chat.py — input filter present"
  fi

  if ! grep -q "NEVER give.*medical advice\|NEVER recommend.*medication\|not a doctor" api/chat.py; then
    echo -e "  ${RED}FAIL${NC}: api/chat.py — system prompt missing medical guardrails"
    FAIL=1
  else
    echo -e "  ${GREEN}OK${NC}: api/chat.py — system prompt guardrails present"
  fi

  if ! grep -q "not medical advice" api/chat.py; then
    echo -e "  ${RED}FAIL${NC}: api/chat.py — missing 'not medical advice' in responses"
    FAIL=1
  else
    echo -e "  ${GREEN}OK${NC}: api/chat.py — response disclaimer present"
  fi
fi
echo ""

# 4. Experiment reports must have limitations
echo "Checking experiment reports..."
for f in $(find data -name "experiment_*_report.md" 2>/dev/null); do
  if ! grep -qi "limitation\|not.*reviewed.*expert\|not.*validated\|not.*medical" "$f"; then
    echo -e "  ${RED}FAIL${NC}: $f — missing limitations section"
    FAIL=1
  else
    echo -e "  ${GREEN}OK${NC}: $f"
  fi
done
echo ""

# 5. Check that hypotheses are never framed as validated
echo "Checking hypothesis language..."
BAD_HYPO="clinically proven\|validated treatment\|confirmed to work\|should be prescribed\|we discovered a cure"
for f in $(find . -name "*.html" -name "*.md" -name "*.py" -not -path "./.git/*" -not -path "./node_modules/*" 2>/dev/null); do
  matches=$(grep -inE "$BAD_HYPO" "$f" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    echo -e "  ${RED}FAIL${NC}: $f — frames hypotheses as validated:"
    echo "$matches" | head -3
    FAIL=1
  fi
done
echo ""

# Summary
echo "=== Summary ==="
if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}All guardrail checks passed.${NC}"
  exit 0
else
  echo -e "${RED}Some guardrail checks failed. Please fix before committing.${NC}"
  echo -e "${YELLOW}Tip: Every HTML page needs a medical disclaimer. Every hypothesis must be framed as unvalidated.${NC}"
  exit 1
fi
