from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from routes import auth, clients, dashboard, balancetes, relatorios, financial_entries, pdf_processor
from routers import monthly_analyses

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="Orion Backend", description="API para sistema de gestão financeira", version="1.0.0")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(balancetes.router, prefix="/api/balancetes", tags=["Balancetes"])
app.include_router(pdf_processor.router, prefix="/api/pdf", tags=["PDF Processing"])
app.include_router(relatorios.router, prefix="/api/relatorios", tags=["Relatórios"])
app.include_router(financial_entries.router, prefix="/api/financial-entries", tags=["FinancialEntries"])
app.include_router(monthly_analyses.router, tags=["Monthly Analyses"])

@app.get("/")
async def root():
    return {"message": "Orion Backend API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
