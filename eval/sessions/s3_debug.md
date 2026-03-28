# Session 3: Debug Race Condition

I'm running the API with gunicorn using 4 worker processes and I'm hitting a bug with the rate limiter.

The issue: Under concurrent requests, some users are able to exceed the rate limit. I ran a load test with 200 concurrent requests from the same user and about 150 got through instead of 100.

I think it's a race condition but I'm not sure where. The rate limiter uses an in-memory dict — could that be the problem with multiple workers?

Can you:
1. Explain exactly what the race condition is
2. Show me the fix
3. Tell me if there are other concurrency issues I should worry about with this architecture
