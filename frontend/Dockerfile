FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# nginx thay ${TRUSTED_PROXY} khi khởi động (chỉ biến đã khai báo, không đụng $remote_addr…)
ENV TRUSTED_PROXY=127.0.0.1/32
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
