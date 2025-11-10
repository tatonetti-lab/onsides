# Database

**Just looking for the data?**
Please visit the [Releases](https://github.com/tatonetti-lab/onsides/releases).

## Database helpers

This directory contains database schemas and helper scripts for SQLite, MySQL, and PostgreSQL.
In addition, there are two scripts for testing (`test.sql`) and summarization (`summarize.sql`).

## ETL Best Practices and Command Formatting

When running ETL processes or database commands:

- **Command Formatting**: Separate commands with line breaks. For commands with options, use indented line breaks for clarity.
  Example:
  ```
  psql -d mydb -U user \
    -c "SELECT * FROM table;" \
    -f script.sql
  ```

- **Thoughtful ETL Execution**: Avoid running PSQL scripts haphazardly. Always:
  - Verify prerequisites (e.g., environment variables, permissions).
  - Use dry-run modes if available.
  - Log outputs for auditing.
  - Test on a subset first for large operations.
  - Ensure idempotency where possible to allow safe reruns.
