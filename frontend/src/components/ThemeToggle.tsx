import { useEffect, useState } from 'react';

const ThemeToggle = () => {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <button 
      onClick={toggleTheme} 
      style={{
        position: 'absolute',
        top: '1rem',
        right: '1rem',
        background: 'transparent',
        border: '1px solid var(--border)',
        color: 'var(--text-main)',
        padding: '0.5rem 1rem',
        borderRadius: '6px',
        cursor: 'pointer',
        width: 'auto',
        marginTop: 0
      }}
    >
      {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
    </button>
  );
};

export default ThemeToggle;
