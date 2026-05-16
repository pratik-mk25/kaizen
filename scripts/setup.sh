#!/bin/bash

# MISSION AVINYA Setup Script

echo "Initializing AVINYA development environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate venv and install dependencies
echo "Installing dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Action Required: Update .env with your Supabase credentials."
else
    echo "Local .env file already exists."
fi

echo "Setup complete! Start the server with:"
echo "source venv/bin/activate"
echo "uvicorn main:app --reload"
