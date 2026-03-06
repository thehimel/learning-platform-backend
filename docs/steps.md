# Steps

## Initialize FastAPI Project

- [chore: set up project structure with initial configuration files](https://github.com/thehimel/learning-platform-api/commit/ba2ac817aa618b6e98f880409484ad96fac24411)
- [feat: add environment configuration and FastAPI setup with CORS support](https://github.com/thehimel/learning-platform-api/commit/7374a80d5d80e26949cb1bd112a2dbad617bca50)

## Configure Docker and Docker Compose

- [chore: add Docker configuration files for development and production environments](https://github.com/thehimel/learning-platform-api/commit/daaf93147060389d3f0e1a93375c3bb18caecf33)

## Setup Database

Setup guide: [sqlalchemy-alembic-async-setup.md](config/sqlalchemy-alembic-async-setup.md)

- [feat: implement async database setup and course model](https://github.com/thehimel/learning-platform-api/commit/e9f67bb4bccf7de14e547ee91205b1a7b9cdf8fd)
- [chore: initialize Alembic](https://github.com/thehimel/learning-platform-api/commit/6ff1b67077f3091ca5949e9ef7356ae121b92b12)
- [feat: update Alembic configuration for async database migrations](https://github.com/thehimel/learning-platform-api/commit/5f8c91ec63447be54cb2bb3a7d185879bad66f3a)
- [feat: create courses table migration](https://github.com/thehimel/learning-platform-api/commit/d4c88a1e61cad06773db900a319da04ac72e71cb)
- [feat: add SSL support for PostgreSQL connections and update environment configuration](https://github.com/thehimel/learning-platform-api/commit/6835f3989e39e6d1429bb6ce6fad7fbef181cf89)

## Implement Authentication and Authorization

- [feat: add user authentication, RBAC, and management endpoints](https://github.com/thehimel/learning-platform-api/commit/68826bc73c8783d1805fbdd5b7d76b6c5cecf6c2)
- [feat: implement password strength validation in user management](https://github.com/thehimel/learning-platform-api/commit/53733a6fe34f6b321b7187392212a9134cc3123b)
- [feat: remove is_superuser column from user model](https://github.com/thehimel/learning-platform-api/commit/ee3739e152e4159c499507037e253c44aeddb89d)
- [feat: require email verification before allowing email self-update](https://github.com/thehimel/learning-platform-api/commit/d01d1cc04d62fc19dbc07d85d0f03526cb552162)
- [feat: enhance authentication security and user management logging](https://github.com/thehimel/learning-platform-api/commit/4878909d09d6fb2b9bd303de15c564f02a9992d0)
- [feat: implement rate limiting using SlowAPI middleware](https://github.com/thehimel/learning-platform-api/commit/50cfb622eda72b494cc49bd16bea6c9645f9d94c)
- [refactor: update JWT access token expiration time to 1 day](https://github.com/thehimel/learning-platform-api/commit/14f22b7b32ba3fd2af1304d33ef9819f2fc915ff)
