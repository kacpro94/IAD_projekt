# Lab 2 — Pipeline Neon → BigQuery przez GitHub Actions

Ten szablon zawiera gotowy pipeline EL (Extract & Load), który:
1. Łączy się z bazą Neon (PostgreSQL) i wyciąga dane z wybranej tabeli.
2. Ładuje je do BigQuery.
3. Jest uruchamiany ręcznie lub według harmonogramu przez GitHub Actions.

Wasze zadanie: uzupełnić oznaczone `TODO` i skonfigurować dwa sekrety w repo.

---

## Krok 1 — Service account w Google Cloud (do BigQuery)

1. Wejdź do [Google Cloud Console](https://console.cloud.google.com) → wybierz swój projekt.
2. Przejdź do **IAM & Admin → Service Accounts → Create Service Account**.
3. Nadaj nazwę (np. `github-actions-loader`).
4. Przypisz rolę **BigQuery Data Editor**.
5. Po utworzeniu konta wejdź w nie → zakładka **Keys → Add Key → Create new key → JSON**.
6. Pobierze się plik `.json` — otwórz go w edytorze tekstu, skopiuj **całą zawartość**.

## Krok 2 — Connection string z Neon

1. Wejdź do panelu Neon → swój projekt → **Connection Details**.
2. Skopiuj connection string w formacie:
   `postgresql://user:password@host/dbname?sslmode=require`

## Krok 3 — Dodanie sekretów w GitHub

W repozytorium na GitHubie:
`Settings → Secrets and variables → Actions → New repository secret`

Dodaj dwa sekrety:

| Nazwa sekretu | Wartość |
|---|---|
| `GCP_SA_KEY` | cała zawartość pliku JSON z Kroku 1 |
| `NEON_CONNECTION_STRING` | connection string z Kroku 2 |

## Krok 4 — Uzupełnienie konfiguracji w kodzie

W pliku `.github/workflows/load.yml` uzupełnij:
- `BQ_PROJECT_ID` — ID Twojego projektu w Google Cloud
- `BQ_DATASET` — nazwa datasetu w BigQuery (np. `landing`)
- `BQ_TABLE` — nazwa tabeli docelowej (np. `posts`)

W pliku `extract_load.py` sprawdź/zmień:
- `SOURCE_TABLE` — nazwa tabeli źródłowej w Neon
- `INCREMENTAL_COLUMN` — kolumna z timestampem, używana przy trybie incremental
- `LOAD_MODE` — `"full_refresh"` na start; zmienicie na `"incremental"` w drugiej części labu

## Krok 5 — Uruchomienie

1. Wejdź w repo na GitHubie → zakładka **Actions**.
2. Wybierz workflow **Load data from Neon to BigQuery**.
3. Kliknij **Run workflow** (uruchomienie ręczne, nie trzeba czekać na harmonogram).
4. Obserwuj logi — powinieneś zobaczyć m.in.:
   ```
   Wyciągnięto X wierszy z Neon (tabela źródłowa: posts)
   Załadowano X wierszy do <projekt>.<dataset>.<tabela> (tryb: full_refresh)
   ```
5. Sprawdź w konsoli BigQuery, czy tabela faktycznie się pojawiła/zaktualizowała.

## Krok 6 — Test trybu incremental

1. W panelu SQL Neon wykonaj ręcznie `INSERT` nowego wiersza do tabeli źródłowej.
2. Zmień `LOAD_MODE = "incremental"` w `extract_load.py`.
3. Uruchom workflow ponownie (`Run workflow`).
4. Sprawdź w logach, że wyciągnięty został tylko nowy wiersz — nie cała tabela.

---

## Typowe problemy

- **Błąd autoryzacji do BigQuery** — sprawdź, czy rola `BigQuery Data Editor` została poprawnie nadana i czy cała zawartość JSON trafiła do sekretu (bez obcięcia).
- **Błąd połączenia z Neon** — sprawdź, czy connection string zawiera `?sslmode=require` na końcu; Neon zwykle tego wymaga.
- **Pusty wynik przy incremental** — upewnij się, że nowy wiersz w Neon ma `created_at` późniejszy niż wszystko, co już jest w BigQuery.
