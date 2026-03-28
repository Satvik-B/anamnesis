# Session 2: Add Rate Limiting

I need to add rate limiting to the API we built. Requirements:

- Rate limit: 100 requests per minute per user (identified by JWT subject claim)
- For unauthenticated endpoints: rate limit by IP address
- Use an in-memory store (dict with timestamps) — no Redis dependency yet
- Apply it as middleware, similar to how we did auth
- Return 429 Too Many Requests with a Retry-After header when limit is exceeded
- Add rate limit headers to all responses: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

Please implement the rate limiter middleware and show how it integrates with the existing auth middleware.
