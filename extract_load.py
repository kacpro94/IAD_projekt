"""
Extract & Load: Neon (PostgreSQL) -> BigQuery

Ten skrypt jest uruchamiany przez GitHub Actions (patrz .github/workflows/load.yml).
Zmienne środowiskowe (NEON_CONNECTION_STRING, BQ_PROJECT_ID, BQ_DATASET, BQ_TABLE)
są ustawiane w kroku workflow, na podstawie GitHub Secrets.

Studenci uzupełniają / modyfikują sekcję "KONFIGURACJA" poniżej.
"""

import os
import psycopg2
import pandas as pd
from google.cloud import bigquery

# ============================================================
# KONFIGURACJA -- tu wprowadzacie zmiany na labie
# ============================================================

NEON_CONNECTION_STRING = os.environ["NEON_CONNECTION_STRING"]
BQ_PROJECT_ID = os.environ["BQ_PROJECT_ID"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_TABLE = os.environ["BQ_TABLE"]

# TODO: nazwa tabeli źródłowej w Neon (ta, którą wypełnialiście w Lab 1)
SOURCE_TABLE = "test"

# TODO: kolumna używana do wykrywania nowych/zmienionych wierszy przy incremental load
INCREMENTAL_COLUMN = "updated_at"

# TODO: "full_refresh" -> zawsze ładuje wszystko od nowa (nadpisuje tabelę w BigQuery)
#       "incremental"  -> ładuje tylko wiersze nowsze niż ostatnio załadowane
LOAD_MODE = "incremental"

# ============================================================
# LOGIKA -- zwykle nie trzeba tego modyfikować
# ============================================================


def get_last_loaded_timestamp(bq_client: bigquery.Client, table_ref: str):
    """Odczytuje maksymalny timestamp już obecny w tabeli docelowej BigQuery.

    Używane tylko w trybie incremental -- pozwala wyciągnąć z Neon
    wyłącznie wiersze nowsze niż to, co już wcześniej załadowano.
    Jeśli tabela w BigQuery jeszcze nie istnieje, zwraca None
    (co w praktyce oznacza "załaduj wszystko").
    """
    query = f"SELECT MAX({INCREMENTAL_COLUMN}) AS max_ts FROM `{table_ref}`"
    try:
        result = bq_client.query(query).result()
        row = next(iter(result))
        return row.max_ts
    except Exception:
        return None


def extract_from_neon(mode: str, last_ts=None) -> pd.DataFrame:
    """Łączy się z bazą Neon i wyciąga dane z tabeli źródłowej."""
    conn = psycopg2.connect(NEON_CONNECTION_STRING)
    try:
        if mode == "incremental" and last_ts is not None:
            query = f"SELECT * FROM {SOURCE_TABLE} WHERE {INCREMENTAL_COLUMN} > %s"
            df = pd.read_sql(query, conn, params=(last_ts,))
        else:
            query = f"SELECT * FROM {SOURCE_TABLE}"
            df = pd.read_sql(query, conn)
    finally:
        conn.close()
    return df


def load_to_bigquery(df: pd.DataFrame, table_ref: str, mode: str):
    """Ładuje DataFrame do BigQuery.

    full_refresh -> WRITE_TRUNCATE (nadpisuje całą tabelę)
    incremental  -> WRITE_APPEND   (dopisuje nowe wiersze)
    """
    bq_client = bigquery.Client()
    write_disposition = (
        bigquery.WriteDisposition.WRITE_TRUNCATE
        if mode == "full_refresh"
        else bigquery.WriteDisposition.WRITE_APPEND
    )
    job_config = bigquery.LoadJobConfig(write_disposition=write_disposition)
    job = bq_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # czeka na zakończenie load jobu
    return job


def main():
    table_ref = f"{BQ_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    bq_client = bigquery.Client()

    last_ts = None
    if LOAD_MODE == "incremental":
        last_ts = get_last_loaded_timestamp(bq_client, table_ref)
        print(f"Ostatni załadowany timestamp w BigQuery: {last_ts}")

    df = extract_from_neon(LOAD_MODE, last_ts)
    print(f"Wyciągnięto {len(df)} wierszy z Neon (tabela źródłowa: {SOURCE_TABLE})")

    if df.empty:
        print("Brak nowych danych do załadowania -- kończę.")
        return

    job = load_to_bigquery(df, table_ref, LOAD_MODE)
    print(f"Załadowano {job.output_rows} wierszy do {table_ref} (tryb: {LOAD_MODE})")


if __name__ == "__main__":
    main()
