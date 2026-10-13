# Database migrations

How to change the database schema with Alembic, plus the day-to-day database commands for this project.

## Concepts in one minute

- **Model**: a Python class in `app/models/` that describes a table (`Conversation`, `Message`).
- **Migration**: a Python file in `alembic/versions/` with two functions: `upgrade()` applies a schema change, `downgrade()` reverts it.
- **Revision**: the ID of a migration (for example `1f0e33ad2b82`). Each migration points to the previous one through `down_revision`, forming a chain.
- **head**: the newest migration in the chain.
- **Autogenerate**: Alembic compares the models (`Base.metadata`, imported in `alembic/env.py`) with the real database and writes a migration with the differences. It is a **draft**, not a finished migration: always read it.

The database does **not** change when you edit a model. It only changes when you apply a migration.

```mermaid
flowchart LR
    A["1. Edit a model<br/>app/models/"] --> B["2. Generate<br/>alembic revision --autogenerate"]
    B --> C["3. Read and fix<br/>alembic/versions/*.py"]
    C --> D["4. Apply<br/>alembic upgrade head"]
    D --> E["5. Test the way back<br/>downgrade -1, upgrade head"]
    E --> F["6. Commit model<br/>and migration together"]
```

## Where to run the commands

Run Alembic **inside the `api` container**. The connection URL in `.env` uses the host name `db`, which only exists inside the Docker network. The `alembic/` folder is mounted into the container, so generated files appear in your local `alembic/versions/` immediately.

```bash
docker compose up -d                    # the stack must be running
docker compose exec api alembic current # every command below follows this pattern
```

All commands below omit the `docker compose exec api` prefix for readability.

<details>
<summary>Running from the host instead (without the container)</summary>

Point `DATABASE_URL` to the published port (`DB_PORT` in `.env`, usually `5432`). Environment variables override `.env`.

```bash
# bash
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/chatbotfastapi" uv run alembic current
```

```powershell
# PowerShell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/chatbotfastapi"
uv run alembic current
Remove-Item Env:DATABASE_URL
```

</details>

## Creating a migration with autogenerate

1. **Edit the model** in `app/models/`. A new model must also be imported in `app/models/__init__.py`, otherwise Alembic does not see it.

2. **Make sure the database is up to date** before generating. Autogenerate compares against the current database, so pending migrations would be generated again.

   ```bash
   alembic upgrade head
   ```

3. **Generate the draft** with a short, imperative message:

   ```bash
   alembic revision --autogenerate -m "add model column to messages"
   ```

   This creates `alembic/versions/<revision>_add_model_column_to_messages.py`.

4. **Read the file** and fix it using the [review checklist](#review-checklist). This step is not optional.

5. **Apply it:**

   ```bash
   alembic upgrade head
   ```

6. **Test that it can be reverted**, then apply it again:

   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```

7. **Commit the model change and the migration in the same commit.**

## Review checklist

Autogenerate only sees part of the schema. In this project's configuration (`alembic/env.py`, Alembic 1.20) it does **not** detect:

| Change | What autogenerate does | What to do |
| --- | --- | --- |
| New `CheckConstraint` on an **existing** table | Nothing. Check-constraint detection is an opt-in plugin and `env.py` does not enable it. On a **new** table it is included inside `create_table`. | Add `op.create_check_constraint(...)` in `upgrade()` and `op.drop_constraint(..., type_="check")` in `downgrade()`. |
| Changed condition of an existing `CheckConstraint` | Nothing, even with the plugin enabled (it compares names only). | Drop and recreate the constraint by hand. |
| Changed `server_default` | Nothing (`compare_server_default` is not enabled). | Use `op.alter_column(..., server_default=...)`. |
| Renamed column or table | A **drop** plus an **add**: the data is lost. | Replace with `op.alter_column(..., new_column_name=...)` or `op.rename_table(...)`. |
| PostgreSQL extensions (`vector`) | Nothing. | `op.execute("CREATE EXTENSION ...")`, as in `141302f1380b_enable_pgvector_extension.py`. |
| Data changes (backfills, fixing values) | Nothing. | Write them with `op.execute(...)`. |
| Unnamed constraints | Unreliable. | Always pass `name=` (for example `ck_messages_role`). |

Also check:

- [ ] `downgrade()` reverts exactly what `upgrade()` does, in reverse order.
- [ ] A new `NOT NULL` column on a table that already has rows has a `server_default` or a backfill, otherwise `upgrade` fails.
- [ ] No unexpected operations (drops of tables or indexes you did not touch).
- [ ] The message in the docstring describes the change.

Example: adding a check constraint to the existing `messages` table.

```python
def upgrade() -> None:
    op.add_column("messages", sa.Column("model", sa.String(length=100), nullable=True))
    op.create_check_constraint(
        "ck_messages_model",
        "messages",
        "(role IN ('assistant', 'tool') AND model IS NOT NULL) "
        "OR (role IN ('user', 'system') AND model IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_messages_model", "messages", type_="check")
    op.drop_column("messages", "model")
```

## Alembic command reference

| Task | Command |
| --- | --- |
| Generate a migration from model changes | `alembic revision --autogenerate -m "message"` |
| Create an empty migration (extensions, data changes) | `alembic revision -m "message"` |
| Apply all pending migrations | `alembic upgrade head` |
| Apply only the next migration | `alembic upgrade +1` |
| Revert the last migration | `alembic downgrade -1` |
| Revert everything (empty schema, **data lost**) | `alembic downgrade base` |
| Show the revision the database is at | `alembic current` |
| List all migrations | `alembic history --verbose` |
| Show the latest migration(s) | `alembic heads` |
| Show one migration | `alembic show <revision>` |
| Check whether models and database are in sync | `alembic check` |
| Print the SQL without running it | `alembic upgrade <from_rev>:<to_rev> --sql` |
| Mark the database as being at a revision without running anything | `alembic stamp <revision>` |

Notes:

- `alembic check` fails if autogenerate would produce a new migration. Useful before committing. It has the same blind spots as the checklist above.
- `stamp` only rewrites the `alembic_version` table. Use it to repair the recorded state, never to "skip" a migration you need.
- If `alembic heads` shows **two** heads, two branches created migrations from the same parent. Edit the `down_revision` of the newest one to point at the other head, or run `alembic merge heads -m "merge"`.

## Other database commands

| Task | Command |
| --- | --- |
| Check the app can connect to the database | `docker compose exec api python -m app.db.check_db` |
| Open a SQL console | `docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'` |
| Database logs | `docker compose logs -f db` |
| **Reset the database (destroys all data)** | `docker compose down -v`, then `docker compose up -d` and `docker compose exec api alembic upgrade head` |

Useful commands inside `psql`:

| Command | Shows |
| --- | --- |
| `\dt` | Tables |
| `\d messages` | Columns, indexes and constraints of a table |
| `\dx` | Installed extensions (should list `vector`) |
| `SELECT * FROM alembic_version;` | Revision the database is at |
| `\q` | Exit |

## Code quality commands

Run on the host (development tools are not installed in the container image).

| Task | Command |
| --- | --- |
| Lint | `uv run ruff check .` |
| Lint and auto-fix | `uv run ruff check . --fix` |
| Format | `uv run ruff format .` |
| Tests | `uv run pytest` |

`alembic/versions/` is excluded from Ruff in `pyproject.toml`, so generated migrations are not reformatted.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Autogenerate produces an empty migration | The model is not imported in `app/models/__init__.py`, or the change is in the checklist's blind spots. |
| Autogenerate repeats changes that already exist | The database is behind. Run `alembic upgrade head` first. |
| `could not translate host name "db"` | Running from the host. Use the container or override `DATABASE_URL`. |
| `Can't locate revision identified by ...` | The database is at a revision whose file no longer exists (deleted or from another branch). Restore the file, or `stamp` to an existing revision. |
| `Multiple head revisions are present` | Two migrations share the same parent. See the note on `alembic heads`. |
| `type "vector" does not exist` | The pgvector migration has not been applied. Run `alembic upgrade head`. |
