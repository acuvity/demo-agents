FROM node:22-alpine
WORKDIR /app
COPY chat_ui/package*.json ./
RUN npm ci
COPY chat_ui/ .

EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
