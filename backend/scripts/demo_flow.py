"""Demo flow: create client (if missing), create monthly_analysis, insert financial_entries,
then call local dashboard endpoint to validate end-to-end flow.
Run from the repository root using: python -m backend.scripts.demo_flow (or run from backend folder)
"""

import os
import sys

# ensure backend folder is on sys.path so 'from database import ...' works
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(HERE)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import get_supabase_client
import requests
import time

sup = get_supabase_client()

# Change these values as needed
CLIENT_UUID = '01283e88-36af-4c95-bb38-03547cb0cca5'
ANALYSIS_REFERENCE_YEAR = 2025
ANALYSIS_REFERENCE_MONTH = 7
CLIENT_NAME = 'Cliente Exemplo (demo)'

print('Starting demo flow...')

# 1) Ensure client exists
print('Checking client...')
client_resp = sup.table('clients').select('*').eq('id', CLIENT_UUID).execute()
if not client_resp.data:
    print('Client not found, creating...')
    insert_resp = sup.table('clients').insert({
        'id': CLIENT_UUID,
        'nome': CLIENT_NAME,
        'email': 'demo@example.com'
    }).execute()
    if insert_resp.error:
        print('Error creating client:', insert_resp.error)
        raise SystemExit(1)
    print('Client created')
else:
    print('Client exists')

# 2) Create monthly_analysis
print('Creating monthly_analysis...')
analysis_payload = {
    'client_id': CLIENT_UUID,
    'report_date': f'{ANALYSIS_REFERENCE_YEAR}-{ANALYSIS_REFERENCE_MONTH:02d}-01',
    'reference_month': ANALYSIS_REFERENCE_MONTH,
    'reference_year': ANALYSIS_REFERENCE_YEAR,
    'client_name': CLIENT_NAME,
    'source_file_path': '/demo/file.pdf',
    'source_file_name': 'file.pdf',
    'status': 'completed',
    'total_receitas': 10000.00,
    'total_despesas': 7000.00,
    'total_entries': 4
}
ins = sup.table('monthly_analyses').insert(analysis_payload).execute()
if ins.error:
    print('Error inserting monthly_analysis:', ins.error)
    # try to locate existing analysis
else:
    print('Inserted monthly_analysis:', ins.data)

# Try to find the numeric analysis id (latest for client and month)
print('Resolving analysis id...')
q = sup.table('monthly_analyses').select('*').eq('client_id', CLIENT_UUID).eq('reference_month', ANALYSIS_REFERENCE_MONTH).eq('reference_year', ANALYSIS_REFERENCE_YEAR).order('id', desc=True).limit(1).execute()
if not q.data:
    print('Failed to find created analysis')
    raise SystemExit(1)
analysis = q.data[0]
analysis_id = analysis.get('id')
print('Analysis id:', analysis_id)

# 3) Insert example financial_entries
print('Inserting financial_entries...')
entries = [
    {
        'analysis_id': analysis_id,
        'client_id': CLIENT_UUID,
        'report_date': analysis['report_date'],
        'main_group': 'RECEITAS',
        'subgroup_1': 'RECEITAS OPERACIONAIS',
        'specific_account': 'Venda A',
        'movement_type': 'Receita',
        'period_value': 6000.00
    },
    {
        'analysis_id': analysis_id,
        'client_id': CLIENT_UUID,
        'report_date': analysis['report_date'],
        'main_group': 'RECEITAS',
        'subgroup_1': 'RECEITAS FINANCEIRAS',
        'specific_account': 'Juros',
        'movement_type': 'Receita',
        'period_value': 4000.00
    },
    {
        'analysis_id': analysis_id,
        'client_id': CLIENT_UUID,
        'report_date': analysis['report_date'],
        'main_group': 'CUSTOS E DESPESAS',
        'subgroup_1': 'CUSTOS OPERACIONAIS',
        'specific_account': 'Matéria-prima',
        'movement_type': 'Despesa',
        'period_value': 3000.00
    },
    {
        'analysis_id': analysis_id,
        'client_id': CLIENT_UUID,
        'report_date': analysis['report_date'],
        'main_group': 'CUSTOS E DESPESAS',
        'subgroup_1': 'DESPESAS OPERACIONAIS',
        'specific_account': 'Aluguel',
        'movement_type': 'Despesa',
        'period_value': 4000.00
    }
]
ins_entries = sup.table('financial_entries').insert(entries).execute()
if ins_entries.error:
    print('Error inserting entries:', ins_entries.error)
else:
    print('Inserted financial_entries')

# 4) Call local dashboard endpoint using client UUID (endpoint resolves latest analysis)
print('Calling dashboard endpoint...')
try:
    resp = requests.get(f'http://127.0.0.1:8000/api/dashboard/{CLIENT_UUID}', timeout=10)
    print('Status:', resp.status_code)
    print('Body:', resp.text)
except Exception as e:
    print('HTTP error:', e)

print('Demo flow finished')
