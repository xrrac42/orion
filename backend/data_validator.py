# -*- coding: utf-8 -*-
"""
Módulo para validar e limpar os dados retornados pela IA.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def clean_and_validate_llm_response(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Valida a estrutura e limpa os campos do JSON retornado pelo LLM.

    Args:
        data: O dicionário JSON parseado da resposta da IA.

    Returns:
        O dicionário com os dados limpos e validados, ou None se a validação falhar.
    """
    if not _validate_basic_structure(data):
        return None

    # Limpa e converte os valores dentro das contas
    cleaned_contas = []
    for conta in data.get("contas", []):
        # --- LÓGICA DE LIMPEZA ADICIONADA ---
        conta["valor_debito"] = _clean_monetary_value(conta.get("valor_debito"))
        conta["valor_credito"] = _clean_monetary_value(conta.get("valor_credito"))
        cleaned_contas.append(conta)
    
    data["contas"] = cleaned_contas
    return data

def _clean_monetary_value(value: Any) -> float:
    """
    Converte um valor monetário (que pode ser string) para float.
    Trata "1.234,56" e "1,234.56".
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            # Remove pontos (milhar) e substitui vírgula (decimal) por ponto
            cleaned_str = value.replace('.', '').replace(',', '.')
            return float(cleaned_str)
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def _validate_basic_structure(data: Dict[str, Any]) -> bool:
    """
    Valida se o dicionário JSON possui os campos e tipos essenciais.
    """
    if not isinstance(data, dict):
        logger.error("Validação falhou: A resposta da IA não é um objeto JSON.")
        return False
        
    required_fields = ["cliente", "data_inicial", "data_final", "contas"]
    for field in required_fields:
        if field not in data:
            logger.error(f"Validação falhou: Campo obrigatório '{field}' ausente no JSON.")
            return False

    if not isinstance(data["contas"], list):
        logger.error("Validação falhou: O campo 'contas' deve ser uma lista.")
        return False

    required_conta_fields = ["grupo_principal", "conta_especifica", "valor_debito", "valor_credito"]
    for i, conta in enumerate(data["contas"]):
        if not isinstance(conta, dict):
            logger.error(f"Validação falhou: O item {i} em 'contas' não é um objeto.")
            return False
        for field in required_conta_fields:
            if field not in conta:
                logger.error(f"Validação falhou: Campo obrigatório '{field}' ausente na conta {i}.")
                return False
    
    return True
