FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if your python app needs them for MySQL/math
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev || true

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure the app can write files to the root dir for persistence
RUN chmod -R 777 /app

# Expose the port your FastAPI/Python app uses
EXPOSE 8001

# Command to run your app
CMD ["python", "app.py"]