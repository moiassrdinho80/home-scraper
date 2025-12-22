FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create directory for database
RUN mkdir -p /app/data

# Default command: run continuously (12-hour loop)
# Override with: docker run ... python main.py --once
CMD ["python", "main.py"]

