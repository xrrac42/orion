# -*- coding: utf-8 -*-
"""
Módulo para aplicar regras de negócio aos dados extraídos pela IA.
"""
from typing import Dict, Any, List

def apply_business_logic(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transforma os lançamentos extraídos pela IA em entradas financeiras prontas para o banco.
    """
    financial_entries = []
    report_date = structured_data.get("data_final")
    
    for conta in structured_data.get("financial_entries", []):
        grupo_principal = conta.get("grupo_principal")
        valor_debito = conta.get("valor_debito", 0.0)
        valor_credito = conta.get("valor_credito", 0.0)
        
        movement_type = None
        period_value = 0.0

        if "RECEITAS" in grupo_principal:
            movement_type = "Receita"
            period_value = valor_credito
        elif "CUSTOS" in grupo_principal or "DESPESAS" in grupo_principal:
            movement_type = "Despesa"
            period_value = valor_debito
        
        if movement_type and period_value > 0:
            entry = {
                "report_date": report_date,
                "main_group": grupo_principal,
                "subgroup_1": conta.get("subgroup_1"),
                "specific_account": conta.get("conta_especifica"),
                "movement_type": movement_type,
                "period_value": period_value,
                "original_data": conta
            }
            financial_entries.append(entry)
            
    return financial_entries