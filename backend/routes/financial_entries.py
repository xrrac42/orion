from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from database import get_supabase_client
import logging
from datetime import date

router = APIRouter()
logger = logging.getLogger(__name__)

class FinancialEntryResponse(BaseModel):
    id: int
    client_id: str
    report_date: date
    main_group: str
    subgroup_1: Optional[str]
    specific_account: str
    movement_type: str
    period_value: float
    original_data: Optional[dict]
    created_at: Optional[str]

@router.get("/cliente/{client_id}", response_model=List[FinancialEntryResponse])
async def get_financial_entries_cliente(
    client_id: str,
    start_date: Optional[date] = Query(None, description="Data inicial (AAAA-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (AAAA-MM-DD)")
):
    """Buscar lançamentos financeiros detalhados do cliente, com filtro de data"""
    try:
        supabase = get_supabase_client()
        query = supabase.table('financial_entries').select('*').eq('client_id', client_id)
        if start_date:
            query = query.gte('report_date', str(start_date))
        if end_date:
            query = query.lte('report_date', str(end_date))
        response = query.order('report_date', desc=False).execute()
        if response.data is None:
            return []
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar financial_entries do cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/summary")
async def get_financial_summary(
    client_id: Optional[str] = Query(None, description="ID do cliente"),
    analysis_id: Optional[int] = Query(None, description="ID da análise mensal"),
    balancete_id: Optional[int] = Query(None, description="ID do balancete específico")
):
    """Resumo financeiro detalhado do cliente/balancete"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('financial_entries')\
                       .select('main_group, subgroup_1, movement_type, period_value, report_date')

        # Prefer analysis_id when provided
        if analysis_id is not None:
            query = query.eq('analysis_id', analysis_id)
        else:
            if not client_id:
                raise HTTPException(status_code=400, detail='client_id or analysis_id is required')
            query = query.eq('client_id', client_id)
        
        if balancete_id:
            # Filtrar por período do balancete
            balancete_response = supabase.table('balancetes')\
                                        .select('ano, mes')\
                                        .eq('id', balancete_id)\
                                        .execute()
            if balancete_response.data:
                balancete = balancete_response.data[0]
                start_date = f"{balancete['ano']}-{balancete['mes']:02d}-01"
                
                # Calcular próximo mês
                next_month = balancete['mes'] + 1
                next_year = balancete['ano']
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                end_date = f"{next_year}-{next_month:02d}-01"
                
                query = query.gte('report_date', start_date)\
                            .lt('report_date', end_date)
        
        response = query.execute()
        
        if not response.data:
            return {
                'total_receitas': 0,
                'total_despesas': 0,
                'lucro_bruto': 0,
                'total_lancamentos': 0,
                'receitas_operacionais': 0,
                'receitas_financeiras': 0,
                'custos_operacionais': 0,
                'despesas_operacionais': 0
            }
        
        # Calcular totais detalhados
        total_receitas = 0
        total_despesas = 0
        receitas_operacionais = 0
        receitas_financeiras = 0
        custos_operacionais = 0
        despesas_operacionais = 0
        
        for entry in response.data:
            valor = entry['period_value']
            
            if entry['movement_type'] == 'Receita':
                total_receitas += valor
                if entry['subgroup_1'] == 'RECEITAS OPERACIONAIS':
                    receitas_operacionais += valor
                elif entry['subgroup_1'] == 'RECEITAS FINANCEIRAS':
                    receitas_financeiras += valor
            else:  # Despesa
                total_despesas += valor
                if entry['subgroup_1'] == 'CUSTOS OPERACIONAIS':
                    custos_operacionais += valor
                elif entry['subgroup_1'] == 'DESPESAS OPERACIONAIS':
                    despesas_operacionais += valor
        
        return {
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'lucro_bruto': total_receitas - total_despesas,
            'total_lancamentos': len(response.data),
            'receitas_operacionais': receitas_operacionais,
            'receitas_financeiras': receitas_financeiras,
            'custos_operacionais': custos_operacionais,
            'despesas_operacionais': despesas_operacionais
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar resumo financeiro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/fluxo_caixa")
async def get_fluxo_caixa(
    client_id: Optional[str] = Query(None, description="ID do cliente"),
    analysis_id: Optional[int] = Query(None, description="ID da análise mensal"),
    balancete_id: Optional[int] = Query(None, description="ID do balancete específico")
):
    """Fluxo de caixa mensal"""
    try:
        supabase = get_supabase_client()
        
        # Buscar dados por mês
        query = """
        SELECT 
            EXTRACT(YEAR FROM report_date) as ano,
            EXTRACT(MONTH FROM report_date) as mes,
            movement_type,
            SUM(period_value) as total
        FROM financial_entries 
        WHERE client_id = %s
        """
        
        if balancete_id:
            # Buscar balancete para filtrar por período
            balancete_response = supabase.table('balancetes')\
                                        .select('ano, mes')\
                                        .eq('id', balancete_id)\
                                        .execute()
            if balancete_response.data:
                balancete = balancete_response.data[0]
                query += f" AND EXTRACT(YEAR FROM report_date) = {balancete['ano']} AND EXTRACT(MONTH FROM report_date) = {balancete['mes']}"
        
        query += " GROUP BY ano, mes, movement_type ORDER BY ano, mes"
        
        # Por ora, vamos usar uma abordagem mais simples
        q = supabase.table('financial_entries').select('report_date, movement_type, period_value')
        if analysis_id is not None:
            q = q.eq('analysis_id', analysis_id)
        else:
            if not client_id:
                raise HTTPException(status_code=400, detail='client_id or analysis_id is required')
            q = q.eq('client_id', client_id)

        entries_response = q.execute()
        
        if not entries_response.data:
            return []
        
        # Agrupar por mês
        monthly_data = {}
        for entry in entries_response.data:
            date_parts = entry['report_date'].split('-')
            year = int(date_parts[0])
            month = int(date_parts[1])
            key = f"{year}-{month:02d}"
            
            if key not in monthly_data:
                monthly_data[key] = {'receitas': 0, 'despesas': 0}
            
            if entry['movement_type'] == 'Receita':
                monthly_data[key]['receitas'] += entry['period_value']
            else:
                monthly_data[key]['despesas'] += entry['period_value']
        
        # Converter para formato esperado
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        result = []
        
        for key, data in sorted(monthly_data.items()):
            year, month = key.split('-')
            month_name = meses[int(month) - 1]
            result.append({
                'mes': month_name,
                'receitas': data['receitas'],
                'despesas': data['despesas']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar fluxo de caixa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/gastos_categoria")
async def get_gastos_categoria(
    client_id: Optional[str] = Query(None, description="ID do cliente"),
    analysis_id: Optional[int] = Query(None, description="ID da análise mensal"),
    balancete_id: Optional[int] = Query(None, description="ID do balancete específico")
):
    """Gastos agrupados por categoria"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('financial_entries')\
                       .select('subgroup_1, specific_account, period_value')\
                       .eq('movement_type', 'Despesa')

        if analysis_id is not None:
            query = query.eq('analysis_id', analysis_id)
        else:
            if not client_id:
                raise HTTPException(status_code=400, detail='client_id or analysis_id is required')
            query = query.eq('client_id', client_id)
        
        if balancete_id:
            # Filtrar por período do balancete
            balancete_response = supabase.table('balancetes')\
                                        .select('ano, mes')\
                                        .eq('id', balancete_id)\
                                        .execute()
            if balancete_response.data:
                balancete = balancete_response.data[0]
                start_date = f"{balancete['ano']}-{balancete['mes']:02d}-01"
                
                # Calcular próximo mês
                next_month = balancete['mes'] + 1
                next_year = balancete['ano']
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                end_date = f"{next_year}-{next_month:02d}-01"
                
                query = query.gte('report_date', start_date)\
                            .lt('report_date', end_date)
        
        response = query.execute()
        
        if not response.data:
            return []
        
        # Agrupar por subgrupo (categoria principal)
        categorias = {}
        for entry in response.data:
            subgrupo = entry['subgroup_1'] or 'OUTROS'
            if subgrupo not in categorias:
                categorias[subgrupo] = {'total': 0, 'contas': {}}
            
            categorias[subgrupo]['total'] += entry['period_value']
            
            # Também agrupar por conta específica dentro do subgrupo
            conta = entry['specific_account']
            if conta not in categorias[subgrupo]['contas']:
                categorias[subgrupo]['contas'][conta] = 0
            categorias[subgrupo]['contas'][conta] += entry['period_value']
        
        # Calcular total geral para percentuais
        total_gastos = sum(cat['total'] for cat in categorias.values())
        
        # Cores pré-definidas para as categorias
        cores = [
            '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', 
            '#F97316', '#EC4899', '#6B7280', '#14B8A6', '#84CC16',
            '#06B6D4', '#EAB308', '#D946EF', '#F43F5E', '#22C55E'
        ]
        
        result = []
        for i, (categoria, dados) in enumerate(sorted(categorias.items(), key=lambda x: x[1]['total'], reverse=True)):
            percentual = (dados['total'] / total_gastos * 100) if total_gastos > 0 else 0
            
            # Preparar detalhamento das contas específicas
            contas_detalhadas = []
            for conta, valor in sorted(dados['contas'].items(), key=lambda x: x[1], reverse=True):
                contas_detalhadas.append({
                    'conta': conta,
                    'valor': valor,
                    'percentual_categoria': (valor / dados['total'] * 100) if dados['total'] > 0 else 0
                })
            
            result.append({
                'categoria': categoria,
                'valor': dados['total'],
                'percentual': percentual,
                'cor': cores[i % len(cores)],
                'contas_detalhadas': contas_detalhadas
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar gastos por categoria: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/analise_detalhada")
async def get_analise_detalhada(
    client_id: Optional[str] = Query(None, description="ID do cliente"),
    analysis_id: Optional[int] = Query(None, description="ID da análise mensal"),
    balancete_id: Optional[int] = Query(None, description="ID do balancete específico")
):
    """Análise detalhada com separação por grupos principais"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('financial_entries')\
                       .select('main_group, subgroup_1, specific_account, movement_type, period_value, report_date')

        if analysis_id is not None:
            query = query.eq('analysis_id', analysis_id)
        else:
            if not client_id:
                raise HTTPException(status_code=400, detail='client_id or analysis_id is required')
            query = query.eq('client_id', client_id)
        
        if balancete_id:
            # Filtrar por período do balancete
            balancete_response = supabase.table('balancetes')\
                                        .select('ano, mes')\
                                        .eq('id', balancete_id)\
                                        .execute()
            if balancete_response.data:
                balancete = balancete_response.data[0]
                start_date = f"{balancete['ano']}-{balancete['mes']:02d}-01"
                
                # Calcular próximo mês
                next_month = balancete['mes'] + 1
                next_year = balancete['ano']
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                end_date = f"{next_year}-{next_month:02d}-01"
                
                query = query.gte('report_date', start_date)\
                            .lt('report_date', end_date)
        
        response = query.execute()
        
        if not response.data:
            return {
                'receitas': {'total': 0, 'subgrupos': []},
                'custos_despesas': {'total': 0, 'subgrupos': []}
            }
        
        # Organizar dados por grupo principal
        analise = {
            'receitas': {'total': 0, 'subgrupos': {}},
            'custos_despesas': {'total': 0, 'subgrupos': {}}
        }
        
        for entry in response.data:
            valor = entry['period_value']
            grupo = 'receitas' if entry['main_group'] == 'RECEITAS' else 'custos_despesas'
            subgrupo = entry['subgroup_1'] or 'OUTROS'
            conta = entry['specific_account']
            
            analise[grupo]['total'] += valor
            
            if subgrupo not in analise[grupo]['subgrupos']:
                analise[grupo]['subgrupos'][subgrupo] = {
                    'total': 0,
                    'contas': {}
                }
            
            analise[grupo]['subgrupos'][subgrupo]['total'] += valor
            
            if conta not in analise[grupo]['subgrupos'][subgrupo]['contas']:
                analise[grupo]['subgrupos'][subgrupo]['contas'][conta] = 0
            analise[grupo]['subgrupos'][subgrupo]['contas'][conta] += valor
        
        # Converter para formato final
        result = {}
        
        for grupo_key, grupo_data in analise.items():
            subgrupos_lista = []
            
            for subgrupo_nome, subgrupo_data in grupo_data['subgrupos'].items():
                contas_lista = []
                
                for conta_nome, conta_valor in sorted(subgrupo_data['contas'].items(), key=lambda x: x[1], reverse=True):
                    contas_lista.append({
                        'conta': conta_nome,
                        'valor': conta_valor,
                        'percentual_subgrupo': (conta_valor / subgrupo_data['total'] * 100) if subgrupo_data['total'] > 0 else 0
                    })
                
                subgrupos_lista.append({
                    'nome': subgrupo_nome,
                    'total': subgrupo_data['total'],
                    'percentual_grupo': (subgrupo_data['total'] / grupo_data['total'] * 100) if grupo_data['total'] > 0 else 0,
                    'contas': contas_lista
                })
            
            # Ordenar subgrupos por valor
            subgrupos_lista.sort(key=lambda x: x['total'], reverse=True)
            
            result[grupo_key] = {
                'total': grupo_data['total'],
                'subgrupos': subgrupos_lista
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar análise detalhada: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/")
async def get_financial_entries(
    client_id: Optional[str] = Query(None, description="ID do cliente"),
    analysis_id: Optional[int] = Query(None, description="ID da análise mensal"),
    balancete_id: Optional[int] = Query(None, description="ID do balancete específico")
):
    """Buscar lançamentos financeiros"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('financial_entries')\
                       .select('*')

        if analysis_id is not None:
            query = query.eq('analysis_id', analysis_id)
        else:
            if not client_id:
                raise HTTPException(status_code=400, detail='client_id or analysis_id is required')
            query = query.eq('client_id', client_id)
        
        if balancete_id:
            # Filtrar por período do balancete
            balancete_response = supabase.table('balancetes')\
                                        .select('ano, mes')\
                                        .eq('id', balancete_id)\
                                        .execute()
            if balancete_response.data:
                balancete = balancete_response.data[0]
                start_date = f"{balancete['ano']}-{balancete['mes']:02d}-01"
                
                # Calcular próximo mês
                next_month = balancete['mes'] + 1
                next_year = balancete['ano']
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                end_date = f"{next_year}-{next_month:02d}-01"
                
                query = query.gte('report_date', start_date)\
                            .lt('report_date', end_date)
        
        response = query.order('report_date', desc=True).execute()
        
        if not response.data:
            return []
        
        return response.data
        
    except Exception as e:
        logger.error(f"Erro ao buscar lançamentos financeiros: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
