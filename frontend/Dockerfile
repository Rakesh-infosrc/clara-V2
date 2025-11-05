# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder
WORKDIR /app

RUN apk add --no-cache libc6-compat \
    && corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/out ./out

EXPOSE 3000
CMD ["serve", "-s", "out", "-l", "3000"]
