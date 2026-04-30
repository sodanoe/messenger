import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

const isAndroid = /Android/i.test(navigator.userAgent);

if (isAndroid) {
  function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
  }
  setVH();
  window.addEventListener('resize', setVH);
  window.addEventListener('orientationchange', setVH);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', setVH);
  }
}

createRoot(document.getElementById('root')).render(<App />);