# Configuration

All configuration is supplied through environment variables. Locally they are read from a `.env` file at the repository root (copy `.env.example`). Docker Compose interpolates the same file and passes the relevant values to the containers.

Settings are declared and validated in `app/config.py` using `pydantic-settings`. A missing required variable fails the application at startup, not at the first request.

## Rule of thumb

Declare a variable only when code uses it. Variables listed under [Planned](#planned) are intentionally not wired up yet.

## Application settings

Declared in `app/config.py`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPEN_ROUTER_API_KEY` | Yes | none | OpenRouter API key. Stored as `SecretStr` so it is masked in logs and reprs. |
| `OPEN_ROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenRouter API base URL. |
| `OPEN_ROUTER_TIMEOUT` | No | `60` | Read timeout in seconds: how long to wait for the model's response. The connect timeout is fixed and short. |
| `DATABASE_URL` | No | `postgresql+asyncpg://postgres:postgres@db:5432/chatbotfastapi` | PostgreSQL connection string. The default targets the `db` Compose service and is for local development only. |
| `DEBUG` | No | `true` | Enables debug behavior. Must be `false` in any shared or production environment. |
| `API_PORT` | No | `8000` | Port the API listens on. |

Unknown variables are ignored (`extra="ignore"`).

## Docker Compose variables

Used by `docker-compose.yml` and the container command, not by `Settings`.

| Variable            | Description                                                                                        |
| ---------------------| ----------------------------------------------------------------------------------------------------|
| `API_HOST`          | Bind address for Uvicorn. Use `0.0.0.0` in containers; `localhost` is not reachable from the host. |
| `API_PORT`          | Port published by Compose and used by Uvicorn.                                                     |
| `DB_PORT`           | Host port mapped to PostgreSQL's `5432`.                                                           |
| `POSTGRES_DB`       | Database name created on first start.                                                              |
| `POSTGRES_USER`     | Database user.                                                                                     |
| `POSTGRES_PASSWORD` | Database password. Change it for anything beyond local use.                                        |

`DATABASE_URL` must be consistent with the `POSTGRES_*` values and the `db` service name.

Compose substitutes unset variables with an empty string without failing. Double-check your `.env` if the stack starts but behaves oddly.

## Planned

Not read by the application yet. Add them to `Settings` when the feature lands.

| Variable | Feature | Notes |
|---|---|---|
| `JWT_SECRET` | Authentication | Make it required (no default). Use a long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_EXPIRATION_TIME` | Authentication | Token lifetime. Define the unit explicitly (seconds or minutes) when introducing it. |
| `CORS_ORIGINS` | Browser clients | Only needed once a frontend on a different origin calls the API. Browsers enforce CORS; tools like Bruno and `/docs` do not need it. |

## Security notes

- Never commit `.env`. Only `.env.example` belongs in version control.
- The default `DATABASE_URL` contains a development password. Override it outside local development.
- Secrets use `SecretStr`; call `.get_secret_value()` only at the point of use.

## Notes

- The Dockerfile doest copy `.env` , so `.env` is not inside the image. Inside the container, configuration must arrive through the Compose `environment` block.
