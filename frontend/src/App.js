import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import '@/App.css';
import ProcessosLive from '@/pages/ProcessosLive';
import Dashboard from '@/pages/Dashboard';
import DetalhesExecucao from '@/pages/DetalhesExecucao';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ProcessosLive />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/execucao/:id" element={<DetalhesExecucao />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;