# Session 4: WebSocket Rate Limiting

I'm adding a WebSocket endpoint for real-time task updates (using flask-socketio). I need rate limiting on WebSocket events too — max 30 events per minute per user.

Please implement the WebSocket rate limiter. Keep in mind any issues we've encountered before with the HTTP rate limiter — I don't want to repeat the same mistakes.
