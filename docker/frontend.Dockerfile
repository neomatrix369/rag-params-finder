# Dashboard — production build with nginx
# Two-stage: build stage compiles React; runtime stage serves via nginx:alpine

FROM node:22-alpine AS build

ARG VITE_API_URL=http://localhost:8001
ARG GIT_COMMIT=unknown

LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

# Copy package files for dependency installation
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies with npm cache mount
# Cache is preserved between builds — npm ci is fast when no lock changes
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Copy source and build
COPY frontend/ .

ENV VITE_API_URL=${VITE_API_URL}

# Build the production bundle
RUN npm run build

# Runtime stage — nginx:alpine serving the static dist/
# This stage is minimal: just nginx + built assets, no node_modules
FROM nginx:alpine

ARG GIT_COMMIT=unknown

LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

# Copy nginx configuration
COPY docker/frontend.nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

EXPOSE 5374

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:5374/ > /dev/null || exit 1

# Start nginx in foreground mode (for Docker)
CMD ["nginx", "-g", "daemon off;"]
