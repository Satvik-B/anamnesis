# Session 1: Project Setup

You are helping me build a REST API for a task management app.

Requirements:
- Flask framework
- JWT authentication using PyJWT
- Middleware pattern for auth (decorator-based, applied per-route)
- SQLite database with SQLAlchemy ORM
- Three models: User, Project, Task
- Task has fields: id, title, description, status (todo/in_progress/done), assigned_to (FK to User), project_id (FK to Project), created_at, updated_at
- RESTful endpoints: CRUD for tasks, list tasks by project, assign task to user
- Use application factory pattern (create_app function)
- Store JWT secret in environment variable JWT_SECRET

Please design the architecture and write the initial project structure with the auth middleware and Task model. Show me the key files.
