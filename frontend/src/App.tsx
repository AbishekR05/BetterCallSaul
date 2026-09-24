import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/landing/Navbar';
import { Hero } from './components/landing/Hero';
import { About } from './components/landing/About';
import { Values } from './components/landing/Values';
import { LegalDomains } from './components/landing/LegalDomains';
import { HowItWorks } from './components/landing/HowItWorks';
import { Plans } from './components/landing/Plans';
import { FinalCTA } from './components/landing/FinalCTA';
import { Footer } from './components/landing/Footer';
import { AuthModal } from './components/landing/AuthModal';
import { AppShell } from './components/app/AppShell';

export const App: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');

  const openAuth = (mode: 'login' | 'register') => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  if (isAuthenticated) {
    return <AppShell />;
  }

  return (
    <div className="landing-layout">
      <Navbar
        onOpenLogin={() => openAuth('login')}
        onOpenRegister={() => openAuth('register')}
      />
      <main>
        <Hero
          onGetStarted={() => openAuth('register')}
          onLearnMore={() => {
            const el = document.getElementById('about');
            el?.scrollIntoView({ behavior: 'smooth' });
          }}
        />
        <About />
        <Values />
        <LegalDomains />
        <HowItWorks />
        <Plans onSelectPlan={() => openAuth('register')} />
        <FinalCTA onGetStarted={() => openAuth('register')} />
      </main>
      <Footer />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </div>
  );
};

export default App;
