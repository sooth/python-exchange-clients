#!/bin/bash

echo "Quick Platform Test"
echo "=================="

# Check backend
echo -n "Backend API: "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

# Check frontend
echo -n "Frontend: "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

# Check API docs
echo -n "API Docs: "
if curl -s http://localhost:8000/api/v1/docs > /dev/null 2>&1; then
    echo "✓ Available"
else
    echo "✗ Not available"
fi

echo ""
echo "If all checks pass, open http://localhost:3000 in your browser!"