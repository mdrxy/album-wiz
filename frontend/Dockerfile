# Official Node.js image
FROM node:20-alpine AS base

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory set above
COPY package.json package-lock.json ./

# Install dependencies *in the container*
# This is done before copying the rest of the application code in order to take
# advantage of Docker’s layer caching mechanism, which will help speed up the build process
# throught the development process
RUN npm install

# Copy the rest of the application code to the working directory
COPY . .

EXPOSE 3000
# COPY /app/build /usr/share/nginx/html
CMD ["npm", "start"]