from database import get_supabase_client

sup = get_supabase_client()
uid='01283e88-36af-4c95-bb38-03547cb0cca5'
found={}
for table in ['file_uploads','clients','user_profiles','monthly_analyses','financial_entries','balancetes']:
    try:
        resp = sup.table(table).select('*').eq('id', uid).execute()
        if resp.data:
            found[table]=resp.data
    except Exception as e:
        # try searching other columns
        try:
            resp2 = sup.table(table).select('*').eq('analysis_id', uid).execute()
            if resp2.data:
                found[f"{table}.analysis_id"] = resp2.data
        except Exception:
            pass
print(found)
