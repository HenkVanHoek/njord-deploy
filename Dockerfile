# Use a slim Python image as a base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file to leverage the build cache
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# We are copying the entire 'src' directory
COPY src/ /app/src/

# This Dockerfile builds an image capable of running scripts.
# The entrypoint will be determined by the 'docker run' command.
