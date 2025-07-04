#!/bin/bash

echo "Running Mock Draft Simulator Tests..."
echo

# Check if pytest is installed
if ! python3 -m pytest --version &> /dev/null; then
    echo "Error: pytest is not installed."
    echo "Please run: pip3 install -r requirements.txt"
    exit 1
fi

# Run all tests with verbose output
echo "Running all tests..."
python3 -m pytest tests/ -v --tb=short

# Check if tests passed
if [ $? -eq 0 ]; then
    echo
    echo "All tests passed!"
else
    echo
    echo "Some tests failed. Please check the output above."
fi