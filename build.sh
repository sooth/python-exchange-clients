#!/bin/bash
# Build script for python-exchange-clients

echo "Building python-exchange-clients package..."

# Clean up old builds
rm -rf build/ dist/ *.egg-info/

# Build the package
python3 -m build

echo "Build complete! Package files are in dist/"
echo ""
echo "To install locally for testing:"
echo "  pip install -e ."
echo ""
echo "To upload to TestPyPI:"
echo "  python3 -m twine upload --repository testpypi dist/*"
echo ""
echo "To upload to PyPI:"
echo "  python3 -m twine upload dist/*"