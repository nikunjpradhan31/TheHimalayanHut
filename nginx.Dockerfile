# Stage 1: Build frontend
FROM node:20-alpine as build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
COPY frontend/.env ./
RUN npm run build

# Stage 2: Nginx reverse proxy + static serving
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
RUN ls -l /etc/nginx/conf.d/
