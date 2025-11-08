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

  useEffect(() => {
    carregarProcessos();
    const interval = setInterval(carregarProcessos, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#ffffff',
      padding: '3rem 2rem',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', marginBottom: '3rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
          <img 
            src="https://inhands.com.br/wp-content/uploads/2023/09/cropped-Logo-InHands-laranja-192x192.png" 
            alt="InHands Logo" 
            style={{ height: '40px', marginRight: '1rem' }}
          />
        </div>
        
        <h1 style={{ 
          fontSize: '2.5rem', 
          fontWeight: '300', 
          color: '#1a1a1a',
          marginBottom: '0.5rem',
          letterSpacing: '-0.02em'
        }}>
          Scraping INPI
        </h1>
        
        <p style={{ 
          fontSize: '1rem', 
          color: '#666',
          marginBottom: '2rem'
        }}>
          Monitoramento em tempo real dos processos indeferidos
        </p>

        <button
          onClick={iniciarScraping}
          disabled={loading}
          style={{
            backgroundColor: '#ff6b35',
            color: 'white',
            border: 'none',
            padding: '0.75rem 2rem',
            fontSize: '1rem',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            fontWeight: '500',
            transition: 'all 0.2s'
          }}
          onMouseOver={(e) => !loading && (e.target.style.backgroundColor = '#ff5722')}
          onMouseOut={(e) => !loading && (e.target.style.backgroundColor = '#ff6b35')}
        >
          {loading ? 'Processando...' : 'Iniciar Scraping'}
        </button>
      </div>

      {/* Table */}
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ 
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#ff6b35' }}>
                <th style={{ 
                  padding: '1rem', 
                  textAlign: 'left', 
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '0.875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  Processo
                </th>
                <th style={{ 
                  padding: '1rem', 
                  textAlign: 'left', 
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '0.875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  Marca
                </th>
                <th style={{ 
                  padding: '1rem', 
                  textAlign: 'left', 
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '0.875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  Email
                </th>
              </tr>
            </thead>
            <tbody>
              {processos.length === 0 ? (
                <tr>
                  <td colSpan="3" style={{ 
                    padding: '3rem', 
                    textAlign: 'center',
                    color: '#999',
                    fontSize: '0.95rem'
                  }}>
                    {loading ? 'Carregando processos...' : 'Nenhum processo encontrado. Clique em "Iniciar Scraping" para começar.'}
                  </td>
                </tr>
              ) : (
                processos.map((processo, index) => (
                  <tr 
                    key={processo.numero_processo || index}
                    style={{ 
                      borderBottom: '1px solid #f0f0f0',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}
                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ 
                      padding: '1rem',
                      color: '#1a1a1a',
                      fontSize: '0.95rem',
                      fontWeight: '500'
                    }}>
                      {processo.numero_processo}
                    </td>
                    <td style={{ 
                      padding: '1rem',
                      color: processo.marca ? '#1a1a1a' : '#ccc',
                      fontSize: '0.95rem'
                    }}>
                      {processo.marca || '-'}
                    </td>
                    <td style={{ 
                      padding: '1rem',
                      color: processo.email ? '#1a1a1a' : '#ccc',
                      fontSize: '0.95rem'
                    }}>
                      {processo.email || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {processos.length > 0 && (
          <div style={{ 
            marginTop: '1.5rem',
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              Total de processos: <strong>{processos.length}</strong>
            </div>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              Com email: <strong>{processos.filter(p => p.email).length}</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcessosLive;
