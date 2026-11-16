# Database migrations

Use Flask-Migrate / Alembic for schema changes. Never use db.create_all() as a production migration mechanism.

Development commands after configuring DATABASE_URL:

```bash
flask --app app db init
flask --app app db migrate -m "initial academic schema"
flask --app app db upgrade
```

Do not run `db init` twice after migration scripts are committed. Review generated migration code before applying it. Back up production databases first.
