'use client';

import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export default function AjudaPage() {
  return (
    <MainLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Ajuda</h1>
            <p className="mt-2 text-gray-600">
              Central de ajuda e documentação do Orion
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>Guia de Início Rápido</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-gray-900">1. Adicionar Clientes</h4>
                    <p className="text-sm text-gray-600">
                      Comece cadastrando os clientes da sua empresa de contabilidade.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">2. Upload de Balancetes</h4>
                    <p className="text-sm text-gray-600">
                      Faça upload dos balancetes mensais em formato PDF.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">3. Visualizar Dashboards</h4>
                    <p className="text-sm text-gray-600">
                      Acesse os dashboards interativos com os dados processados.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Suporte Técnico</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-gray-900">E-mail</h4>
                    <p className="text-sm text-gray-600">suporte@orion.com.br</p>
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Telefone</h4>
                    <p className="text-sm text-gray-600">(11) 3000-0000</p>
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Horário de Atendimento</h4>
                    <p className="text-sm text-gray-600">
                      Segunda a Sexta: 9h às 18h
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
