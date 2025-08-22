# -*- coding: utf-8 -*-
"""
Módulo para aplicar regras de negócio aos dados extraídos pela IA.
"""
from typing import Dict, Any, Optional, List

def apply_business_logic(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aplica regras de negócio para transformar os dados da IA em entradas financeiras prontas para o banco.

    Args:
        structured_data: Dicionário validado vindo do llm_analyzer.

    Returns:
        Uma lista de dicionários, onde cada um representa um lançamento financeiro.
    """
    financial_entries = []
    
    # Extrai informações de cabeçalho que serão usadas para todas as entradas
    report_date = structured_data.get("data_final")
    
    for conta in structured_data.get("contas", []):
        grupo_principal = conta.get("grupo_principal")
        valor_debito = conta.get("valor_debito", 0.0)
        valor_credito = conta.get("valor_credito", 0.0)
        
        movement_type = None
        period_value = 0.0

        # --- LÓGICA CORRIGIDA ---
        # 1. Determina o tipo de movimento com base no grupo principal.
        # 2. Atribui o valor correto (débito para despesa, crédito para receita).
        if grupo_principal == "RECEITAS":
            movement_type = "Receita"
            # Receitas são baseadas no valor de CRÉDITO do período
            period_value = valor_credito
        elif grupo_principal == "CUSTOS E DESPESAS":
            movement_type = "Despesa"
            # Despesas são baseadas no valor de DÉBITO do período
            period_value = valor_debito
        
        # Apenas adiciona a entrada se ela for de um tipo válido e tiver um valor
        if movement_type and period_value > 0:
            entry = {
                "report_date": report_date,
                "main_group": grupo_principal,
                "subgroup_1": conta.get("subgrupo_1"),
                "specific_account": conta.get("conta_especifica"),
                "movement_type": movement_type,
                "period_value": period_value,
                "original_data": conta  # Guarda o JSON original para auditoria
            }
            financial_entries.append(entry)
            
    return financial_entries
