# Use official Python 3.11 slim image
# We pin to 3.11 specifically because our dependencies
# are fully compatible — avoids the pkg_resources issue
# we hit with Python 3.14 locally
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first — Docker caches this layer
# so pip install only re-runs when requirements.txt changes
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY app/ ./app/
COPY slo/ ./slo/
COPY ai/ ./ai/

# Set environment variables inside the container
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Expose the port uvicorn will listen on
EXPOSE 8000

# Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]