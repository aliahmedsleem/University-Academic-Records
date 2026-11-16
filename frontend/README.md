# UARMS Arabic administration UI

React + TypeScript + Vite. Right-to-left responsive dashboard, muted teal/slate palette, login, and authenticated CRUD for departments, stages and courses.

## Start
```bash
npm install
npm run dev
```
Run Flask on port 5000 in parallel. Vite proxies `/api` to Flask. Visit http://127.0.0.1:5173

## Current scope
One administrator identity from environment variables; roles and user management are not implemented yet. Do not expose this development build publicly or upload real student records. See docs/security/README.md.
