"""Non-destructive upgrade for installations created before paper domains."""
from sqlalchemy import inspect, text


def ensure_paper_domain_column(engine):
    with engine.begin() as connection:
        if not inspect(connection).has_table("papers"):
            return
        if "domain" not in {c["name"] for c in inspect(connection).get_columns("papers")}:
            qualifier = "IF NOT EXISTS " if connection.dialect.name == "postgresql" else ""
            connection.execute(text(f"ALTER TABLE papers ADD COLUMN {qualifier}domain VARCHAR(80)"))
