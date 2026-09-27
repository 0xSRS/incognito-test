import { Pool } from "pg";

declare global {
  // Persist the pool across hot reloads in development
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
}

function getPool(): Pool {
  if (process.env.NODE_ENV === "production") {
    return new Pool({ connectionString: process.env.DATABASE_URL });
  }

  // In dev, cache on globalThis so Turbopack hot reloads don't exhaust connections
  if (!globalThis._pgPool) {
    globalThis._pgPool = new Pool({ connectionString: process.env.DATABASE_URL });
  }
  return globalThis._pgPool;
}

export const pool = getPool();
