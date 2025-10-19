# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables (these can be overridden in docker-compose.yml)
ENV TELEGRAM_BOT_TOKEN=""
ENV ODDS_API_KEY=""
ENV APIFY_API_TOKEN=""
ENV GEMINI_API_KEY=""
ENV SUPABASE_DB_URL=""
ENV PA_USERNAME=""

# Run the application using Gunicorn
# This is the command that will be executed when the container starts
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
