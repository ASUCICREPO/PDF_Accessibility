# Use an official Node.js runtime with a newer version as the base image
FROM node:20

# Set the working directory in the container
WORKDIR /app

# Install required system dependencies for building native modules
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    libsqlite3-dev

# Copy package.json and packa

COPY package*.json ./

# Install dependencies (force better-sqlite3 to build from source if necessary)
RUN npm install 

# Set environment variables
ENV AWS_REGION="us-east-1"

# Copy the rest of the application source code
COPY . .

# Define the command to run the app
CMD ["node", "alt-text.js"]
