# Dashboard — dev server with /api proxy to Compose service "server"
FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

ENV VITE_DEV_PROXY_TARGET=http://server:8001

EXPOSE 5374

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5374"]
