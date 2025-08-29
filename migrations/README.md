Migration guidance

Files:
- 20250829_add_raw_fields.sql: adiciona `raw_analysis` (jsonb) e `file_upload_id` (bigint) à tabela `monthly_analyses`.

Apply locally (psql, with env vars or connection string):

Windows PowerShell example:

```powershell
# Exemplo com psql (substitua os valores adequados)
$PG_CONN = "postgresql://postgres:password@localhost:5432/yourdb"
psql $PG_CONN -f migrations/20250829_add_raw_fields.sql
```

If using Supabase CLI:

```powershell
supabase db remote set <CONN_STRING>
psql <CONN_STRING> -f migrations/20250829_add_raw_fields.sql
```

Notes:
- The migration is additive and safe to run multiple times (uses IF NOT EXISTS).
- After applying, update any insertion code to populate `raw_analysis` and `file_upload_id` when available.
