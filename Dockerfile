FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libtorrent-rasterbar-dev \
    python3-libtorrent \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY config/ ./config/
COPY frontend/dist/ ./frontend/dist/

# Create data directories
RUN mkdir -p data/torrents data/uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
