# ReviewAI database migrations

Run migrations from this directory so Alembic resolves `alembic.ini` and the
application package consistently:

```bash
cd backend
APP_ENV=production DATABASE_URL='postgresql://USER:PASSWORD@PRIVATE_RDS_HOST:5432/reviewai?sslmode=require' alembic upgrade head
```

For AWS, retrieve the AWS-managed RDS master secret into the current shell and
construct `DATABASE_URL` only for the migration process; do not put the
password in a file. Run the command from a host or container with private VPC
connectivity to RDS. The migration environment rejects the local default URL
and local PostgreSQL hosts for production and staging.

The application uses `Base.metadata` only for metadata inspection and
development initialization. Production startup skips `create_all`; schema
changes must be applied explicitly with Alembic.
