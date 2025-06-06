# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory to project root
WORKDIR /formava_ai_trainer

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

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