import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ProcessosLive.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProcessosLive = () => {
  const [processos, setProcessos] = useState([]);
  const [loading, setLoading] = useState(false);

  const carregarProcessos = async () => {
    try {
      const response = await axios.get(`${API}/inpi/executions`);
      if (response.data && response.data.length > 0) {
        const ultimaExecucao = response.data[0];
        const detalhes = await axios.get(`${API}/inpi/executions/${ultimaExecucao.id}`);
        setProcessos(detalhes.data.processos || []);
      }
    } catch (error) {
      console.error('Erro ao carregar processos:', error);
    }
  };

  const iniciarScraping = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/inpi/scrape`);
      // Atualizar a cada 5 segundos
      const interval = setInterval(carregarProcessos, 5000);
      setTimeout(() => {
        clearInterval(interval);
        setLoading(false);
      }, 180000); // 3 minutos
    } catch (error) {
      console.error('Erro:', error);
      setLoading(false);
    }
  };

  const extrairPlanilha = async () => {
    try {
      const response = await axios.get(`${API}/inpi/executions`);
      if (response.data && response.data.length > 0) {
        const ultimaExecucao = response.data[0];
        // Download do XLSX
        window.open(`${API}/inpi/executions/${ultimaExecucao.id}/download_xlsx`, '_blank');
      } else {
        alert('Nenhuma execução encontrada para exportar.');
      }
    } catch (error) {
      console.error('Erro ao extrair planilha:', error);
      alert('Erro ao extrair planilha. Tente novamente.');
    }
  };

  useEffect(() => {
    carregarProcessos();
    const interval = setInterval(carregarProcessos, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="processos-live-container">
      {/* Header */}
      <header className="processos-header">
        <img 
          src="https://inhands.com.br/wp-content/uploads/2021/09/inhands.svg" 
          alt="Logo da InHands" 
          width="160"
          height="55"
        />
      </header>

      {/* Content */}
      <section className="processos-content">
        <h1 className="processos-title">Scraping INPI</h1>
        <p className="processos-subtitle">Consulte os processos indeferidos e o andamento da extração.</p>

        <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', marginBottom: '40px' }}>
          <button
            onClick={iniciarScraping}
            disabled={loading}
            className="btn-primary-custom"
          >
            {loading ? 'Processando...' : 'Iniciar Scraping'}
          </button>

          <button
            onClick={extrairPlanilha}
            disabled={processos.length === 0}
            className="btn-secondary-custom"
          >
            Extrair planilha
          </button>
        </div>

        <div className="central-box">
          <div className="table-responsive">
            <table className="table-custom">
              <thead>
                <tr>
                  <th>Processo</th>
                  <th>Marca</th>
                  <th>Email</th>
                </tr>
              </thead>
              <tbody>
                {processos.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="empty-state">
                      {loading ? 'Carregando processos...' : 'Nenhum processo encontrado. Clique em "Iniciar Scraping" para começar.'}
                    </td>
                  </tr>
                ) : (
                  processos.map((processo, index) => (
                    <tr key={processo.numero_processo || index}>
                      <td>{processo.numero_processo}</td>
                      <td>{processo.marca || '-'}</td>
                      <td>{processo.email || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {processos.length > 0 && (
            <div className="stats-wrapper">
              <div className="small-text">
                Total de processos: <strong>{processos.length}</strong>
              </div>
              <div className="small-text">
                Com email: <strong>{processos.filter(p => p.email).length}</strong>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default ProcessosLive;
