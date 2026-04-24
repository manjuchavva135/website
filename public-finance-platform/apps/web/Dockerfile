FROM node:20-alpine

WORKDIR /app

COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/shared-ts/package.json ./packages/shared-ts/package.json

RUN corepack enable && pnpm install --filter @public-finance/web... --frozen-lockfile=false

COPY . .

WORKDIR /app/apps/web
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD node -e "fetch('http://127.0.0.1:3000/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"

CMD ["pnpm", "dev", "-H", "0.0.0.0", "-p", "3000"]
