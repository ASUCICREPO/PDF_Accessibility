# Use an official Node.js runtime as the base image
FROM node:16

# Set the working directory in the container to /app
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install any needed packages specified in package.json
RUN npm install
ENV AWS_REGION="us-east-1"
# Bundle the app source inside the Docker image
# (Make sure you have a .dockerignore file to avoid copying node_modules)
COPY . .


# Define the command to run the app
CMD [ "node", "alt-text.js" ]
