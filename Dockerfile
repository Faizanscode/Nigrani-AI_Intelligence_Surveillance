# Use official Python runtime as a parent image (CUDA enabled if you want GPU, otherwise standard Python)
# For CPU only (lighter):
FROM python:3.10-slim

# Install system dependencies required for OpenCV, PyTorch, and AI models
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir keeps the docker image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code and ai_engine
# We copy from the root to ensure both backend and ai_engine modules are included
COPY backend/ /app/backend/
COPY ai_engine/ /app/ai_engine/
COPY data/ /app/data/

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
