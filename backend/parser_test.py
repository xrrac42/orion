import re
import pdfplumber
import json
from datetime import datetime

def parse_balancete_for_db(pdf_path):
    """Parser adaptado para as tabelas do banco de dados"""
    data = {
        "empresa": None,
        "periodo": None,
        "monthly_analysis": {},
        "financial_entries": []  # Lista de entradas para inserir no banco
    }

    # Regex para capturar as linhas de conta
    conta_pattern = re.compile(
        r"^(.+?)\s+-\s+\[(\d+)\]\s+([\d.,]+[DC]?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+[DC]?)$"
    )

    # Mapeamento de códigos para grupos principais
    codigo_to_group = {
        "4": {"main_group": "RECEITAS", "movement_type": "Receita"},
        "5": {"main_group": "CUSTOS E DESPESAS", "movement_type": "Despesa"}  # Vamos separar depois
    }

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        current_subgroup = None

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            # Captura nome da empresa
            if data["empresa"] is None:
                m = re.search(r"^(.*?)\s+\(\d+\)", text, re.MULTILINE)
                if m:
                    data["empresa"] = m.group(1).strip()

            # Captura período
            if data["periodo"] is None:
                m = re.search(r"Balancete Analítico de (\d{2}/\d{2}/\d{4}) até (\d{2}/\d{2}/\d{4})", text)
                if m:
                    data["periodo"] = {"inicio": m.group(1), "fim": m.group(2)}

            # Nota: a extração de `monthly_analysis` foi movida para parser_test2.py
            # para manter este teste focado apenas em `financial_entries`.

            # Processa linhas de receitas e despesas/custos
            lines = text.split('\n')
            for raw_line in lines:
                line = re.sub(r'\s{3,}', ' ', raw_line).strip()
                
                if not line:
                    continue

                # Verifica se é uma linha de conta
                match = conta_pattern.search(line)
                
                if match:
                    descricao = match.group(1).strip()
                    codigo = match.group(2)
                    saldo_anterior = match.group(3)
                    debito = match.group(4)
                    credito = match.group(5)
                    saldo_atual = match.group(6)

                    # Filtra apenas códigos 4 (receitas) e 5 (custos/despesas)
                    primeiro_digito = codigo[0] if codigo else "0"
                    
                    if primeiro_digito not in ["4", "5"]:
                        continue

                    # Determina o grupo e tipo de movimento
                    group_info = codigo_to_group[primeiro_digito]
                    
                    # Para códigos 5, refina o tipo baseado na descrição
                    movement_type = group_info["movement_type"]
                    main_group = group_info["main_group"]
                    
                    if primeiro_digito == "5":
                        # Refina entre Custo e Despesa baseado na descrição
                        if any(palavra in descricao.upper() for palavra in ["CMV", "CUSTO", "MERCADORIA"]):
                            movement_type = "Custo"
                            main_group = "CUSTOS"
                        else:
                            movement_type = "Despesa"
                            main_group = "DESPESAS"

                    # Calcula o valor do período (débito - crédito para receitas, crédito - débito para custos/despesas)
                    debito_val = parse_value(debito)
                    credito_val = parse_value(credito)
                    
                    if primeiro_digito == "4":  # Receitas
                        period_value = credito_val - debito_val
                    else:  # Custos/Despesas
                        period_value = debito_val - credito_val

                    # Determina subgrupo baseado na descrição
                    if descricao.isupper() and len(codigo) <= 5:
                        current_subgroup = descricao
                        subgroup_1 = None  # É o próprio subgrupo principal
                    else:
                        subgroup_1 = current_subgroup

                    # Cria entrada para o banco
                    entry = {
                        "main_group": main_group,
                        "subgroup_1": subgroup_1,
                        "specific_account": descricao,
                        "movement_type": movement_type,
                        "period_value": period_value,
                        "original_data": {
                            "codigo": codigo,
                            "saldo_anterior": saldo_anterior,
                            "debito": debito,
                            "credito": credito,
                            "saldo_atual": saldo_atual
                        }
                    }
                    
                    data["financial_entries"].append(entry)

    return data


# parse_monthly_analysis moved to parser_test2.py


def parse_value(value_str):
    """Converte string de valor brasileiro para float"""
    if not value_str:
        return 0.0
    
    # Remove D/C e espaços
    cleaned = re.sub(r'[DC\s]', '', value_str)
    
    # Converte formato brasileiro (1.234,56) para float
    if ',' in cleaned:
        # Separa parte inteira e decimal
        parts = cleaned.split(',')
        integer_part = parts[0].replace('.', '')  # Remove separadores de milhares
        decimal_part = parts[1] if len(parts) > 1 else '00'
        return float(f"{integer_part}.{decimal_part}")
    else:
        # Apenas parte inteira
        return float(cleaned.replace('.', ''))


def format_for_database(parsed_data, client_id=None, created_by=None):
    """Formata os dados para inserção no banco"""
    
    if not parsed_data["periodo"]:
        raise ValueError("Período não encontrado no balancete")
    
    # Extrai data de referência
    data_fim = parsed_data["periodo"]["fim"]
    date_obj = datetime.strptime(data_fim, "%d/%m/%Y")
    
    # Dados para monthly_analyses
    monthly_analysis = {
        "client_id": client_id,
        "report_date": date_obj.date(),
        "reference_month": date_obj.month,
        "reference_year": date_obj.year,
        "client_name": parsed_data["empresa"],
        "status": "completed",
        "source_file_path": "uploads/balancete.pdf",  # Ajustar conforme necessário
        "source_file_name": "BALANCETE UNITY.pdf",
        "total_receitas": parsed_data["monthly_analysis"].get("total_receitas", 0),
        "total_despesas": parsed_data["monthly_analysis"].get("total_despesas", 0),
        "total_entries": len(parsed_data["financial_entries"]),
        "created_by": created_by
    }
    
    # Dados para financial_entries
    financial_entries = []
    for entry in parsed_data["financial_entries"]:
        financial_entry = {
            "client_id": client_id,
            "report_date": date_obj.date(),
            "main_group": entry["main_group"],
            "subgroup_1": entry["subgroup_1"],
            "specific_account": entry["specific_account"],
            "movement_type": entry["movement_type"],
            "period_value": entry["period_value"],
            "original_data": entry["original_data"],
            "created_by": created_by
        }
        financial_entries.append(financial_entry)
    
    return {
        "financial_entries": financial_entries
    }


def debug_balancete_simple(pdf_path):
    """Debug simples para ver se consegue capturar algo"""
    conta_pattern = re.compile(
        r"^(.+?)\s+-\s+\[(\d+)\]\s+([\d.,]+[DC]?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+[DC]?)$"
    )
    
    matches_found = 0
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:2]):  # Apenas primeiras 2 páginas
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for j, raw_line in enumerate(lines):
                line = re.sub(r'\s{3,}', ' ', raw_line).strip()
                
                if '[' in line and ']' in line:
                    match = conta_pattern.search(line)
                    if match:
                        matches_found += 1
                        codigo = match.group(2)
                        descricao = match.group(1)
                        
                        # Mostra apenas receitas e custos/despesas
                        if codigo.startswith(('4', '5')):
                            print(f"✓ Página {i+1}, Linha {j+1}")
                            print(f"   Código: {codigo}")
                            print(f"   Descrição: {descricao}")
                            print(f"   Valores: {match.group(3)} | {match.group(4)} | {match.group(5)} | {match.group(6)}")
                            print()
    
    print(f"Total de matches encontrados: {matches_found}")
    return matches_found > 0


# Teste
print("=== DEBUG SIMPLES ===")
if debug_balancete_simple("BALANCETE UNITY.pdf"):
    print("\n=== EXECUTANDO PARSER COMPLETO (financial_entries) ===")
    resultado = parse_balancete_for_db("BALANCETE UNITY.pdf")

    # Salva somente as entradas financeiras
    out = {
        "empresa": resultado.get("empresa"),
        "periodo": resultado.get("periodo"),
        "financial_entries": resultado.get("financial_entries", [])
    }
    with open("balancete_financial_entries.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    print(f"Empresa: {out['empresa']}")
    print(f"Período: {out['periodo']}")
    print(f"Total de entradas: {len(out['financial_entries'])}")
    print("Arquivo salvo: balancete_financial_entries.json")
else:
    print("Nenhuma linha foi capturada. Verifique o formato do PDF.")