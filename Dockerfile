# Use the official Python image as the base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /Health-Tracker

# Copy the application files into the working directory
COPY . /Health-Tracker

# Install the application dependencies
RUN pip install -r requirements.txt

# Define the entry point for the container
CMD ["python3", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]