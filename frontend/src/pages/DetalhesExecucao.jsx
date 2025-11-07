import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { ArrowLeft, Download, Loader2, Mail, FileText } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DetalhesExecucao = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const carregarDetalhes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/inpi/executions/${id}`);
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      toast.error('Erro ao carregar detalhes da execução');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarDetalhes();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-white animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="bg-white/10 backdrop-blur-md border-white/20 max-w-md w-full">
          <CardContent className="py-12 text-center">
            <p className="text-white text-lg">Execução não encontrada</p>
            <Button onClick={() => navigate('/')} className="mt-4" data-testid="back-btn">
              Voltar ao Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { execucao, processos } = data;

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Button
            onClick={() => navigate('/')}
            variant="ghost"
            className="text-white hover:bg-white/10 mb-4"
            data-testid="back-to-dashboard-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar ao Dashboard
          </Button>
          
          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
            <h1 className="text-4xl font-bold text-white mb-2" data-testid="execucao-title">
              Semana {execucao.semana}/{execucao.ano}
            </h1>
            <p className="text-white/80 text-lg">
              {processos.length} processos de indeferimento
            </p>
            
            {execucao.status === 'concluido' && processos.length > 0 && (
              <Button
                onClick={() => window.open(`${API}/inpi/executions/${id}/xlsx`, '_blank')}
                className="mt-4 bg-white text-purple-600 hover:bg-white/90 font-semibold"
                data-testid="download-xlsx-details-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                Baixar Planilha XLSX
              </Button>
            )}
          </div>
        </div>

        {/* Lista de Processos */}
        <div className="space-y-4">
          {processos.length === 0 ? (
            <Card className="bg-white/10 backdrop-blur-md border-white/20">
              <CardContent className="py-12 text-center">
                <FileText className="w-16 h-16 text-white/50 mx-auto mb-4" />
                <p className="text-white text-lg">Nenhum processo encontrado</p>
              </CardContent>
            </Card>
          ) : (
            processos.map((processo, index) => (
              <Card
                key={processo.id}
                className="bg-white/10 backdrop-blur-md border-white/20"
                data-testid={`processo-card-${index}`}
              >
                <CardHeader>
                  <CardTitle className="text-white text-xl">
                    {processo.marca}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-white/60 text-sm mb-1">Número do Processo</p>
                      <p className="text-white font-mono" data-testid={`processo-numero-${index}`}>
                        {processo.numero_processo}
                      </p>
                    </div>
                    
                    {processo.email && (
                      <div>
                        <p className="text-white/60 text-sm mb-1">Email</p>
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-white/60" />
                          <p className="text-white" data-testid={`processo-email-${index}`}>
                            {processo.email}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default DetalhesExecucao;