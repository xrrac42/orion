# backend/python_parser.py
import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

def _limpar_valor(valor_str: str) -> float:
    try:
        return float(valor_str.strip().upper().replace('D', '').replace('C', '').replace('.', '').replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

def parse_balancete_from_text(text_content: str) -> Optional[Dict[str, Any]]:
    dados = { "cliente": None, "data_final": None, "resumo_periodo": {}, "financial_entries": [] }

    # --- 1. Extrair Metadados (Regex mais tolerante) ---
    # CORREÇÃO: Usamos re.MULTILINE para que o `^` funcione em cada linha, não só na primeira.
    match_cliente = re.search(r"^(.*?)\s*\(\d+\)", text_content, re.MULTILINE)
    if match_cliente:
        dados["cliente"] = match_cliente.group(1).strip()
        logger.info(f"Parser encontrou o cliente: {dados['cliente']}")
    else:
        logger.warning("Parser não conseguiu encontrar o nome do cliente no texto.")

    match_data = re.search(r"de \d{2}/\d{2}/\d{4} até (\d{2}/\d{2}/\d{4})", text_content)
    if match_data:
        dia, mes, ano = match_data.group(1).split('/')
        dados["data_final"] = f"{ano}-{mes}-{dia}"

    # --- 2. Extrair o Resumo Final ---
    try:
        resumo_texto = text_content.split("Valores do Período")[1]
        match_receita = re.search(r"Receita.*?(?P<valor>[\d.,]+C)", resumo_texto, re.DOTALL)
        match_despesa = re.search(r"Despesa/Custo.*?(?P<valor>[\d.,]+D)", resumo_texto, re.DOTALL)
        match_lucro = re.search(r"Lucro.*?(?P<valor>[\d.,]+)", resumo_texto, re.DOTALL)

        if match_receita and match_despesa and match_lucro:
            dados["resumo_periodo"] = {
                "total_receitas": _limpar_valor(match_receita.group('valor')),
                "total_despesas_custos": _limpar_valor(match_despesa.group('valor')),
                "lucro_periodo": _limpar_valor(match_lucro.group('valor'))
            }
            logger.info("Resumo do período extraído com sucesso.")
        else:
            logger.warning("Parser do resumo falhou em encontrar todos os campos.")
    except IndexError:
        logger.error("A âncora 'Valores do Período' não foi encontrada.")
    
    # --- 3. Extrair Lançamentos ---
    linhas = text_content.split('\n')
    grupo_principal_atual = None
    subgrupo_1_atual = None
    padrao_lancamento = re.compile(r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+(?:D|C)?)$")

    for linha in linhas:
        linha_limpa = linha.strip()
        if not linha_limpa or "Saldo Anterior" in linha_limpa: continue
        if linha_limpa.startswith("RECEITAS - [") or linha_limpa.startswith("CUSTOS E DESPESAS - ["):
            grupo_principal_atual = linha_limpa.split('-')[0].strip()
            subgrupo_1_atual = None
            continue
        if grupo_principal_atual and "- [" in linha_limpa and not padrao_lancamento.search(linha_limpa):
            subgrupo_1_atual = linha_limpa.split('-')[0].strip()
            continue
        match = padrao_lancamento.search(linha_limpa)
        if match and grupo_principal_atual:
            descricao = linha_limpa[:match.start()].strip()
            descricao = re.sub(r'-\s*\[\d+\]\s*$', '', descricao).strip()
            debito_str, credito_str, _ = match.groups()
            debito = _limpar_valor(debito_str)
            credito = _limpar_valor(credito_str)
            if debito > 0 or credito > 0:
                dados["financial_entries"].append({
                    "grupo_principal": grupo_principal_atual,
                    "subgrupo_1": subgrupo_1_atual or grupo_principal_atual,
                    "conta_especifica": descricao, "valor_debito": debito, "valor_credito": credito
                })
    return dados