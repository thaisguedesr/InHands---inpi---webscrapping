import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Calendar, Download, FileText, RefreshCw, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [execucoes, setExecucoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const navigate = useNavigate();

  const carregarExecucoes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/inpi/executions`);
      setExecucoes(response.data);
    } catch (error) {
      console.error('Erro ao carregar execuções:', error);
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const iniciarScrapingManual = async () => {
    try {
      setScraping(true);
      await axios.post(`${API}/inpi/scrape`);
      toast.success('Scraping iniciado! Atualize a página em alguns instantes.');
      setTimeout(carregarExecucoes, 3000);
    } catch (error) {
      console.error('Erro ao iniciar scraping:', error);
      toast.error('Erro ao iniciar scraping');
    } finally {
      setScraping(false);
    }
  };

  useEffect(() => {
    carregarExecucoes();
    // Atualizar a cada 30 segundos
    const interval = setInterval(carregarExecucoes, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status) => {
    const statusMap = {
      'concluido': { variant: 'default', icon: CheckCircle2, label: 'Concluído', className: 'bg-green-500' },
      'processando': { variant: 'secondary', icon: Loader2, label: 'Processando', className: 'bg-blue-500' },
      'erro': { variant: 'destructive', icon: XCircle, label: 'Erro', className: 'bg-red-500' }
    };
    
    const config = statusMap[status] || statusMap['processando'];
    const Icon = config.icon;
    
    return (
      <Badge className={`${config.className} text-white`} data-testid={`status-badge-${status}`}>
        <Icon className="w-3 h-3 mr-1" />
        {config.label}
      </Badge>
    );
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 mb-8 shadow-xl border border-white/20">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2" data-testid="page-title">
                INPI Mailing - Indeferimentos
              </h1>
              <p className="text-white/80 text-lg">
                Monitoramento semanal de processos de marca indeferidos
              </p>
            </div>
            <Button
              onClick={iniciarScrapingManual}
              disabled={scraping}
              className="bg-white text-purple-600 hover:bg-white/90 font-semibold px-6 py-6 text-lg"
              data-testid="manual-scraping-btn"
            >
              {scraping ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <RefreshCw className="w-5 h-5 mr-2" />
                  Executar Agora
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 mb-8 border border-white/20">
          <div className="flex items-start gap-3">
            <Calendar className="w-5 h-5 text-white mt-0.5" />
            <div>
              <p className="text-white font-medium mb-1">Execução Automática</p>
              <p className="text-white/70 text-sm">
                O sistema executa automaticamente toda terça-feira às 08:00 (horário de Brasília)
              </p>
            </div>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-12 h-12 text-white animate-spin" />
          </div>
        )}

        {/* Lista de Execuções */}
        {!loading && (
          <div className="grid gap-6">
            {execucoes.length === 0 ? (
              <Card className="bg-white/10 backdrop-blur-md border-white/20">
                <CardContent className="py-12 text-center">
                  <FileText className="w-16 h-16 text-white/50 mx-auto mb-4" />
                  <p className="text-white text-lg">Nenhuma execução encontrada</p>
                  <p className="text-white/60 mt-2">Clique em "Executar Agora" para iniciar o scraping</p>
                </CardContent>
              </Card>
            ) : (
              execucoes.map((exec) => (
                <Card
                  key={exec.id}
                  className="bg-white/10 backdrop-blur-md border-white/20 hover:bg-white/15 transition-all cursor-pointer"
                  onClick={() => navigate(`/execucao/${exec.id}`)}
                  data-testid={`execucao-card-${exec.id}`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <CardTitle className="text-white text-2xl mb-2">
                          Semana {exec.semana}/{exec.ano}
                        </CardTitle>
                        <CardDescription className="text-white/70 text-base">
                          Executado em {formatarData(exec.data_execucao)}
                        </CardDescription>
                      </div>
                      {getStatusBadge(exec.status)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="bg-white/5 rounded-lg p-4">
                        <p className="text-white/60 text-sm mb-1">Processos Encontrados</p>
                        <p className="text-white text-2xl font-bold" data-testid={`total-processos-${exec.id}`}>
                          {exec.total_processos}
                        </p>
                      </div>
                      {exec.xml_url && (
                        <div className="bg-white/5 rounded-lg p-4 md:col-span-2">
                          <p className="text-white/60 text-sm mb-1">URL do XML</p>
                          <p className="text-white text-sm truncate">{exec.xml_url}</p>
                        </div>
                      )}
                    </div>

                    {exec.mensagem_erro && (
                      <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-4">
                        <p className="text-white font-medium mb-1">Erro:</p>
                        <p className="text-white/90 text-sm">{exec.mensagem_erro}</p>
                      </div>
                    )}

                    {exec.status === 'concluido' && exec.total_processos > 0 && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`${API}/inpi/executions/${exec.id}/xlsx`, '_blank');
                        }}
                        className="w-full bg-white/20 hover:bg-white/30 text-white border border-white/30"
                        data-testid={`download-xlsx-btn-${exec.id}`}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Baixar Planilha XLSX
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;