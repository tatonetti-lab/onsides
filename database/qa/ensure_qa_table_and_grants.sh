#!/usr/bin/env bash
set -euo pipefail

# ensure_qa_table_and_grants.sh
# Idempotently ensure the QA log table exists and grant rw_grp the necessary privileges.
# Usage: ./ensure_qa_table_and_grants.sh [-d PGDATABASE] [-p PGPORT] [-u PGUSER]

PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}
PGUSER=${PGUSER:-postgres}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "Ensuring onsides.z_qa_faers_wc_import_log exists (running DDL as $PGUSER on $PGDATABASE:$PGPORT)"
PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -f "$SCRIPT_DIR/z_qa_faers_wc_import_log.sql"

echo "Applying migration (rename old column if needed)"
PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -f "$SCRIPT_DIR/migrate_laers_to_onsides_release_version.sql"

echo "Granting schema usage and table privileges to rw_grp"
PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -c "GRANT USAGE ON SCHEMA onsides TO rw_grp;"
PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -c "GRANT SELECT, INSERT ON TABLE onsides.z_qa_faers_wc_import_log TO rw_grp;"

echo "Done."
