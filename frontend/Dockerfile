# Dev image for the React frontend.
# node_modules is installed inside the image (not mounted) so it doesn't get
# clobbered by your host OS's node_modules; source code is mounted separately.

FROM node:20-slim

WORKDIR /app

# Copy only package files first so npm ci is cached unless deps change
COPY package.json package-lock.json ./
RUN npm ci

# Actual source comes in via the volume mount in docker-compose.yml.

EXPOSE 3000

# CHOKIDAR_USEPOLLING helps file-watching work reliably across Docker's
# filesystem boundary, especially if you're on Mac/Windows.
ENV CHOKIDAR_USEPOLLING=true

CMD ["npm", "start"]