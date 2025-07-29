#!/usr/bin/env python3
"""Run the backend with environment variables from .env file"""

import os
import sys
import subprocess
from pathlib import Path

# Change to backend directory
backend_dir = Path(__file__).parent
os.chdir(backend_dir)

# Load .env file manually - check both backend and parent directories
env_vars = os.environ.copy()
env_files = [
    backend_dir / '.env',
    backend_dir.parent / '.env'
]

for env_file in env_files:
    if env_file.exists():
        print(f"Loading environment from {env_file}...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Skip lines with JSON arrays for now
                    if '=' in line and not line.startswith('BACKEND_CORS_ORIGINS'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value
                        if key in ['BITUNIX_API_KEY', 'BITUNIX_SECRET_KEY']:
                            print(f"Loaded {key}: {value[:10]}...")

# Set the BACKEND_CORS_ORIGINS as a proper JSON string
env_vars['BACKEND_CORS_ORIGINS'] = '["http://localhost:3000", "http://localhost:8000"]'

# Check parent environment for API keys - ALWAYS use parent if available
if 'BITUNIX_API_KEY' in os.environ:
    env_vars['BITUNIX_API_KEY'] = os.environ['BITUNIX_API_KEY']
    print(f"Using BITUNIX_API_KEY from parent environment: {env_vars['BITUNIX_API_KEY'][:10]}...")
else:
    print("WARNING: BITUNIX_API_KEY not found in parent environment")

if 'BITUNIX_SECRET_KEY' in os.environ:
    env_vars['BITUNIX_SECRET_KEY'] = os.environ['BITUNIX_SECRET_KEY']
    print(f"Using BITUNIX_SECRET_KEY from parent environment: {env_vars['BITUNIX_SECRET_KEY'][:10]}...")
else:
    print("WARNING: BITUNIX_SECRET_KEY not found in parent environment")

print(f"\nEnvironment check:")
print(f"BITUNIX_API_KEY set: {'BITUNIX_API_KEY' in env_vars}")
print(f"BITUNIX_SECRET_KEY set: {'BITUNIX_SECRET_KEY' in env_vars}")

# Run uvicorn with the environment
cmd = [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8001', '--reload']
print(f"\nStarting backend on port 8001...")
print(f"Command: {' '.join(cmd)}")

subprocess.run(cmd, env=env_vars)