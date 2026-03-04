# Use the official Python slim image (smaller footprint than the full image)
FROM python:3.14-slim

# Set the working directory for subsequent commands
WORKDIR /usr/src/app

# Copy dependencies first to leverage layer caching (code changes won't trigger reinstall)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Start Uvicorn (bind to 0.0.0.0 so the app is reachable from outside the container)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
