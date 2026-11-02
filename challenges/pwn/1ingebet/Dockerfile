FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

COPY src/package.json src/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund

COPY src/ ./

RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8080

CMD ["node", "server.js"]
