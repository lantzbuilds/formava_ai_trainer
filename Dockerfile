# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory to project root
WORKDIR /formava_ai_trainer

# Install system dependencies with retry logic and better error handling
RUN apt-get update --fix-missing || apt-get update || true && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    software-properties-common \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with retry logic
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data/vectorstore

# Expose the port Gradio runs on
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Command to run the application
CMD ["python", "-m", "app.main"]