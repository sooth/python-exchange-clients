#!/bin/bash

echo "Frontend Validation Report"
echo "=========================="
echo ""

# Type checking
echo "1. TypeScript Type Checking"
echo "---------------------------"
npx tsc --noEmit 2>&1 | head -20
echo ""

# ESLint
echo "2. ESLint Analysis"
echo "------------------"
npx eslint . --ext .ts,.tsx,.js,.jsx --max-warnings 0 2>&1 | head -30
echo ""

# Check for console.log
echo "3. Console.log Check"
echo "-------------------"
grep -r "console.log" --include="*.ts" --include="*.tsx" --exclude-dir=node_modules --exclude-dir=.next . | wc -l | xargs -I {} echo "Found {} console.log statements"
echo ""

# Check for any type
echo "4. TypeScript 'any' Usage"
echo "------------------------"
grep -r ": any" --include="*.ts" --include="*.tsx" --exclude-dir=node_modules --exclude-dir=.next . | wc -l | xargs -I {} echo "Found {} uses of 'any' type"
echo ""

echo "To fix issues run:"
echo "  npm run lint:fix     - Auto-fix ESLint issues"
echo "  npm run format       - Format with Prettier"