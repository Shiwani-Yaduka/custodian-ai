# Web app image: build the React app, then serve it with NGINX.
# Build context is the web/ folder.

# ---- Stage 1: build the static files ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# The browser calls the services through NGINX on the SAME address, so these are relative paths.
# (They are baked in at build time. The names match what your React code reads.)
ARG VITE_CAPTURE_DETECT_URL=/api/capture
ARG VITE_RISK_ENGINE_URL=/api/risk
ARG VITE_INVESTIGATOR_URL=/api/investigator
ARG VITE_WARN_ESCALATE_URL=/api/warn
ARG VITE_REVIEW_REPORT_URL=/api/review

ENV VITE_CAPTURE_DETECT_URL=$VITE_CAPTURE_DETECT_URL \
    VITE_RISK_ENGINE_URL=$VITE_RISK_ENGINE_URL \
    VITE_INVESTIGATOR_URL=$VITE_INVESTIGATOR_URL \
    VITE_WARN_ESCALATE_URL=$VITE_WARN_ESCALATE_URL \
    VITE_REVIEW_REPORT_URL=$VITE_REVIEW_REPORT_URL \
    VITE_CAPTURE_URL=$VITE_CAPTURE_DETECT_URL \
    VITE_RISK_URL=$VITE_RISK_ENGINE_URL \
    VITE_WARN_URL=$VITE_WARN_ESCALATE_URL \
    VITE_REVIEW_URL=$VITE_REVIEW_REPORT_URL

# Copy MediaPipe WASM files from node_modules into public/wasm for offline client detection
RUN mkdir -p public/wasm && cp -r node_modules/@mediapipe/tasks-vision/wasm/* public/wasm/

RUN npm run build

# ---- Stage 2: tiny non-root web server ----
FROM nginxinc/nginx-unprivileged:1.27-alpine
USER root
RUN apk update && apk upgrade --no-cache
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
