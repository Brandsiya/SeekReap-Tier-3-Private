#!/bin/bash
echo "=== SEEKREAP TIER-3 STRUCTURE CHECK ==="
echo ""

echo "1. Checking directory structure..."
ls -la
echo ""

echo "2. Checking envelope_consumers..."
ls -la envelope_consumers/
echo ""

echo "3. Checking semantic_processors..."
ls -la semantic_processors/
echo ""

echo "4. Checking scoring_engines..."
ls -la scoring_engines/
echo ""

echo "5. Checking examples..."
ls -la examples/
echo ""

echo "6. Checking README.md..."
head -20 README.md
echo ""

echo "7. Checking __init__.py..."
cat __init__.py
echo ""

echo "=== STRUCTURE CHECK COMPLETE ==="
echo "Total files created: $(find . -type f -name "*.py" -o -name "*.md" -o -name "*.txt" | wc -l)"
