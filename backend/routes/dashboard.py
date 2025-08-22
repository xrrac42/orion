# -*- coding: utf-8 -*-
"""
Endpoint da API para fornecer dados para o dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models # Supondo que seus modelos SQLAlchemy estejam aqui
from sqlalchemy import func
from datetime import date

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/{analysis_id}")
def get_dashboard_data(analysis_id: int, db: Session = Depends(get_db)):
    """
    Retorna todos os dados agregados para um balancete específico (analysis_id)
    para popular o dashboard completo do cliente.
    """
    try:
        # 1. Busca a análise principal para obter metadados
        analysis = db.query(models.MonthlyAnalysis).filter(models.MonthlyAnalysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhuma análise encontrada com o ID {analysis_id}"
            )

        # 2. Calcula os KPIs (Receita e Despesa Total)
        kpi_query = db.query(
            models.FinancialEntry.movement_type,
            func.sum(models.FinancialEntry.period_value).label("total")
        ).filter(
            models.FinancialEntry.analysis_id == analysis_id
        ).group_by(
            models.FinancialEntry.movement_type
        ).all()

        kpis = {
            "receita_total": 0.0,
            "despesa_total": 0.0,
        }
        for movement_type, total in kpi_query:
            if movement_type == 'Receita':
                kpis["receita_total"] = float(total or 0.0)
            elif movement_type == 'Despesa':
                kpis["despesa_total"] = float(total or 0.0)
        kpis["resultado_periodo"] = kpis["receita_total"] - kpis["despesa_total"]

        # 3. Composição das Receitas (por subgrupo)
        receitas_composicao = db.query(
            func.coalesce(models.FinancialEntry.subgroup_1, 'Outras Receitas').label("subgrupo"),
            func.sum(models.FinancialEntry.period_value).label("valor")
        ).filter(
            models.FinancialEntry.analysis_id == analysis_id,
            models.FinancialEntry.movement_type == 'Receita'
        ).group_by(
            "subgrupo"
        ).all()
        total_receita = kpis["receita_total"] or 1
        receitasComposicao = [
            {
                "subgrupo": r.subgrupo,
                "valor": float(r.valor),
                "percentual": (float(r.valor) / total_receita) * 100 if total_receita else 0
            }
            for r in receitas_composicao
        ]

        # 4. Principais Despesas (por subgrupo)
        despesas_principais = db.query(
            func.coalesce(models.FinancialEntry.subgroup_1, 'Outras Despesas').label("subgrupo"),
            func.sum(models.FinancialEntry.period_value).label("valor")
        ).filter(
            models.FinancialEntry.analysis_id == analysis_id,
            models.FinancialEntry.movement_type == 'Despesa'
        ).group_by(
            "subgrupo"
        ).order_by(
            func.sum(models.FinancialEntry.period_value).desc()
        ).limit(10).all()
        despesasPrincipais = [
            {
                "subgrupo": d.subgrupo,
                "valor": float(d.valor)
            }
            for d in despesas_principais
        ]

        # 5. Detalhes das contas (apenas despesas)
        contas_detalhes = db.query(
            models.FinancialEntry.specific_account.label("conta"),
            func.sum(models.FinancialEntry.period_value).label("valor"),
            func.coalesce(models.FinancialEntry.subgroup_1, 'Outros').label("subgrupo")
        ).filter(
            models.FinancialEntry.analysis_id == analysis_id,
            models.FinancialEntry.movement_type == 'Despesa'
        ).group_by(
            "conta", "subgrupo"
        ).all()
        contasDetalhes = [
            {
                "conta": c.conta,
                "valor": float(c.valor),
                "subgrupo": c.subgrupo
            }
            for c in contas_detalhes
        ]

        # 6. Período (data inicial e final, se disponível)
        periodo = None
        if hasattr(analysis, "data_inicial") and analysis.data_inicial:
            periodo = f"{analysis.data_inicial.strftime('%d/%m/%Y')} a {analysis.report_date.strftime('%d/%m/%Y')}"
        else:
            periodo = analysis.report_date.strftime("%d/%m/%Y")

        return {
            "cliente": analysis.client_name,
            "periodo": periodo,
            "kpis": kpis,
            "receitasComposicao": receitasComposicao,
            "despesasPrincipais": despesasPrincipais,
            "contasDetalhes": contasDetalhes
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno ao processar os dados do dashboard."
        )

