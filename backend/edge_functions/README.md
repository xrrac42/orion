# Edge Function: process_balancete

Esta função é acionada por um trigger de upload no Supabase Storage (bucket `balancetes`).

- Extrai o texto do PDF.
- Chama a API Gemini para análise e estruturação dos dados.
- Aplica as regras de negócio e insere o resultado na tabela `balancetes_processados`.

## Espera-se que o evento recebido tenha:
- `file_path`: caminho do arquivo PDF no storage
- `client_id`: id do cliente (opcional, pode ser extraído do path)

## Dependências
- `supabase-py`
- `PyPDF2`
- `requests`
- `python-dotenv`

## Exemplo de chamada local
```python
from process_balancete import handler
handler({"file_path": "public/123/BALANCETE UNITY.pdf", "client_id": "123"}, None)
```
