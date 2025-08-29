import fitz
import re
import json

def extrair_analise_balancete(caminho_pdf):
    doc = fitz.open(caminho_pdf)
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text()

    texto_completo = re.sub(r"\s+", " ", texto_completo).strip()

    # Localiza a última ocorrência de "Análise do Balancete"
    idx = texto_completo.lower().rfind("análise do balancete")
    if idx == -1:
        raise ValueError("Seção 'Análise do Balancete' não encontrada.")

    trecho = texto_completo[idx:]

    # Extrair resumo do balancete
    ativo = re.search(r"Ativo\s*-+>\s*([\d\.,]+[CD])", trecho)
    passivo = re.search(r"Passivo\s*-+>\s*([\d\.,]+[CD])", trecho)
    receita = re.search(r"\bReceita\s*-+>\s*([\d\.,]+[CD])", trecho)
    despesa = re.search(r"Despesa\s*-+>\s*([\d\.,]+[CD])", trecho)

    # Captura valores do período aceitando espaços extras e ordem valor -> palavra
    bloco_periodo = re.search(
        r"Valores\s+do\s+Período.*?([\d\.,]+[CD])\s+Receita.*?([\d\.,]+[CD])\s+Despesa/Custo.*?([\d\.,]+)\s+Lucro",
        trecho,
        flags=re.IGNORECASE
    )

    receita_periodo = despesa_custo_periodo = lucro_periodo = None
    if bloco_periodo:
        receita_periodo = bloco_periodo.group(1)
        despesa_custo_periodo = bloco_periodo.group(2)
        lucro_periodo = bloco_periodo.group(3)

    resultado = {
        "resumo_balancete": {
            "ativo": ativo.group(1) if ativo else None,
            "passivo": passivo.group(1) if passivo else None,
            "despesa": despesa.group(1) if despesa else None,
            "receita": receita.group(1) if receita else None
        },
        "valores_periodo": {
            "receita": receita_periodo,
            "despesa_custo": despesa_custo_periodo,
            "lucro": lucro_periodo
        }
    }

    return json.dumps(resultado, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    caminho_pdf = "BALANCETE UNITY.pdf"
    print(extrair_analise_balancete(caminho_pdf))
