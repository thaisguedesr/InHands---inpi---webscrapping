import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import '@/App.css';
import Dashboard from '@/pages/Dashboard';
import DetalhesExecucao from '@/pages/DetalhesExecucao';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/execucao/:id" element={<DetalhesExecucao />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;