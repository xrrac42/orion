from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import PyPDF2
import re
from decimal import Decimal
import logging
from database import get_supabase_client

router = APIRouter()
logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.patterns = {
            'receita': [
                r'receita.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'vendas.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'faturamento.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'entrada.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
            ],
            'despesa': [
                r'despesa.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'gasto.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'pagamento.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'custo.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'saída.*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
            ],
            'categoria': [
                r'folha\s+de\s+pagamento',
                r'aluguel',
                r'material',
                r'fornecedor',
                r'energia\s+elétrica',
                r'telefone',
                r'internet',
                r'combustível',
                r'manutenção'
            ]
        }

    def parse_currency(self, value_str: str) -> float:
        """Converte string de moeda brasileira para float"""
        try:
            # Remove pontos de milhares e substitui vírgula por ponto
            clean_value = value_str.replace('.', '').replace(',', '.')
            return float(clean_value)
        except:
            return 0.0

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extrai texto do PDF"""
        try:
            supabase = get_supabase_client()
            # Baixar arquivo do Supabase Storage
            response = supabase.storage.from_('balancetes').download(file_path)
            
            # Processar PDF
            from io import BytesIO
            pdf_reader = PyPDF2.PdfReader(BytesIO(response))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text.lower()
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {e}")
            return ""

    def extract_financial_data(self, text: str) -> Dict[str, Any]:
        """Extrai dados financeiros do texto"""
        receitas = []
        despesas = []
        categorias = {}

        # Buscar receitas
        for pattern in self.patterns['receita']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                valor = self.parse_currency(match.group(1))
                if valor > 0:
                    receitas.append(valor)

        # Buscar despesas
        for pattern in self.patterns['despesa']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                valor = self.parse_currency(match.group(1))
                if valor > 0:
                    despesas.append(valor)

        # Buscar categorias
        for categoria in self.patterns['categoria']:
            matches = re.finditer(categoria, text, re.IGNORECASE)
            if matches:
                # Procurar valor próximo à categoria
                for match in matches:
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end]
                    
                    valor_pattern = r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
                    valor_matches = re.findall(valor_pattern, context)
                    if valor_matches:
                        valor = self.parse_currency(valor_matches[-1])  # Pega o último valor encontrado
                        if valor > 0:
                            categorias[categoria.replace('\\s+', ' ')] = valor

        return {
            'total_receitas': sum(receitas),
            'total_despesas': sum(despesas),
            'receitas_detalhadas': receitas,
            'despesas_detalhadas': despesas,
            'categorias': categorias
        }

@router.post("/process/{balancete_id}")
async def process_balancete_pdf(balancete_id: int):
    """Processa PDF do balancete e extrai dados financeiros"""
    try:
        supabase = get_supabase_client()
        
        # Buscar balancete
        balancete_response = supabase.table('balancetes')\
                                   .select('*')\
                                   .eq('id', balancete_id)\
                                   .execute()
        
        if not balancete_response.data:
            raise HTTPException(status_code=404, detail="Balancete não encontrado")
        
        balancete = balancete_response.data[0]
        file_upload_id = balancete.get('file_upload_id')
        
        if not file_upload_id:
            raise HTTPException(status_code=400, detail="Balancete não tem arquivo associado")
        
        # Buscar file_upload
        file_upload_response = supabase.table('file_uploads')\
                                      .select('*')\
                                      .eq('id', file_upload_id)\
                                      .execute()
        
        if not file_upload_response.data:
            raise HTTPException(status_code=400, detail="Arquivo não encontrado")
        
        file_upload = file_upload_response.data[0]
        file_path = file_upload['file_path']
        
        # Processar PDF
        processor = PDFProcessor()
        text = processor.extract_text_from_pdf(file_path)
        
        if not text:
            raise HTTPException(status_code=400, detail="Não foi possível extrair texto do PDF")
        
        # Extrair dados financeiros
        financial_data = processor.extract_financial_data(text)
        
        # Atualizar balancete com dados extraídos
        update_data = {
            'total_receitas': financial_data['total_receitas'],
            'total_despesas': financial_data['total_despesas']
        }
        
        supabase.table('balancetes')\
                .update(update_data)\
                .eq('id', balancete_id)\
                .execute()
        
        # Criar entradas financeiras detalhadas
        entries = []
        analysis_id = None
        try:
            bal_resp = supabase.table('balancetes').select('analysis_id').eq('id', balancete_id).single().execute()
            if bal_resp and getattr(bal_resp, 'data', None):
                analysis_id = bal_resp.data.get('analysis_id')
        except Exception:
            analysis_id = None

        if not analysis_id:
            client_name = None
            try:
                cli = supabase.table('clients').select('nome').eq('id', balancete['client_id']).single().execute()
                if cli and getattr(cli, 'data', None):
                    client_name = cli.data.get('nome')
            except Exception:
                client_name = None

            analysis_payload = {
                'client_id': balancete['client_id'],
                'report_date': f"{balancete['ano']}-{balancete['mes']:02d}-01",
                'reference_month': int(balancete['mes']),
                'reference_year': int(balancete['ano']),
                'client_name': client_name or balancete['client_id'],
                'source_file_path': file_path,
                'source_file_name': file_upload.get('file_name'),
                'status': 'completed',
                'total_receitas': financial_data.get('total_receitas', 0),
                'total_despesas': financial_data.get('total_despesas', 0),
                'total_entries': 0
            }
            try:
                create_analysis_resp = supabase.table('monthly_analyses').insert(analysis_payload).execute()
                if create_analysis_resp and getattr(create_analysis_resp, 'data', None) and len(create_analysis_resp.data) > 0:
                    analysis_id = create_analysis_resp.data[0].get('id')
                    try:
                        supabase.table('balancetes').update({'analysis_id': analysis_id}).eq('id', balancete_id).execute()
                    except Exception:
                        pass
            except Exception:
                analysis_id = None
        
        # Receitas
        for i, receita in enumerate(financial_data.get('receitas_detalhadas', [])):
            entries.append({
                'analysis_id': analysis_id,
                'client_id': balancete['client_id'],
                'report_date': f"{balancete['ano']}-{balancete['mes']:02d}-01",
                'main_group': 'RECEITAS',
                'specific_account': f'Receita {i+1}',
                'movement_type': 'Receita',
                'period_value': receita
            })
        
        # Despesas
        for i, despesa in enumerate(financial_data.get('despesas_detalhadas', [])):
            entries.append({
                'analysis_id': analysis_id,
                'client_id': balancete['client_id'],
                'report_date': f"{balancete['ano']}-{balancete['mes']:02d}-01",
                'main_group': 'CUSTOS E DESPESAS',
                'specific_account': f'Despesa {i+1}',
                'movement_type': 'Despesa',
                'period_value': despesa
            })
        
        # Despesas por categoria
        for categoria, valor in financial_data.get('categorias', {}).items():
            entries.append({
                'analysis_id': analysis_id,
                'client_id': balancete['client_id'],
                'report_date': f"{balancete['ano']}-{balancete['mes']:02d}-01",
                'main_group': 'CUSTOS E DESPESAS',
                'subgroup_1': categoria.title(),
                'specific_account': categoria.title(),
                'movement_type': 'Despesa',
                'period_value': valor
            })
        
        # Inserir entradas financeiras
        if entries:
            supabase.table('financial_entries').insert(entries).execute()
        
        # Atualizar status do upload
        supabase.table('file_uploads')\
                .update({
                    'status': 'completed',
                    'entries_created': len(entries),
                    'processing_completed_at': 'now()'
                })\
                .eq('id', file_upload_id)\
                .execute()
        
        return {
            'message': 'PDF processado com sucesso',
            'dados_extraidos': financial_data,
            'entradas_criadas': len(entries)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar PDF do balancete {balancete_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
