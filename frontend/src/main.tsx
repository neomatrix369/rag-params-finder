import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';
import { getApiBaseUrl } from './services/apiClient';
import { devInfo } from './utils/devLog';

devInfo('App', `boot — api=${getApiBaseUrl()} mode=${import.meta.env.MODE}`);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
