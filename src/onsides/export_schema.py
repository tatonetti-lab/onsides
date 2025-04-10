from sqlalchemy.schema import CreateTable

from onsides.db import SQLModel


def export_schema_for_dialect(dialect, output_filename):
    """
    Exports the DDL for all tables defined in SQLModel.metadata
    to the specified file using the provided dialect.

    For PostgreSQL, this replaces Enum columns with inline VARCHAR types
    using a CHECK constraint (via native_enum=False).
    """
    with open(output_filename, "w") as f:
        for table in SQLModel.metadata.sorted_tables:
            ddl = str(CreateTable(table).compile(dialect=dialect))
            f.write(ddl + ";\n\n")
