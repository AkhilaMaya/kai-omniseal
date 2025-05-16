# Use official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install Flask
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into /app
COPY . .

# Run the app
CMD ["python", "kai_omniseal.py"]
