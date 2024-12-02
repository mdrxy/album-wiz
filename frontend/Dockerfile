# Official Node.js image
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package.json package-lock.json ./

# Install dependencies
# This is done before copying the rest of the application code in order to take
# advantage of Docker’s layer caching mechanism, which will help speed up the build process
# throught the development process
RUN npm install

# Copy the rest of the application code to the working directory
COPY . .

# Build the React app for production
# Creates the production ready files in the /app/build folder
RUN npm run build

# Use an Nginx image to serve the built files
FROM nginx:alpine

# Copy the built React files (from the previous stage) to the Nginx default public folder
# This is done to serve the React app using Nginx
COPY --from=0 /app/build /usr/share/nginx/html

# Expose the port that Nginx will run on
EXPOSE 80

# Start Nginx and begin serving the app
CMD ["nginx", "-g", "daemon off;"]