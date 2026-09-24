import React from 'react';
import ladyJusticeHero from '../../assets/lady_justice_hero.jpg';
import './Hero.css';

interface HeroProps {
  onGetStarted: () => void;
  onLearnMore: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted, onLearnMore }) => {
  return (
    <section className="hero-section">
      <div className="container hero-grid">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-pulse"></span>
            <span>Grounded Indian Penal Code Intelligence</span>
          </div>

          <h1 className="hero-title">
            Deterministic Legal Research & <span className="hero-highlight">Statutory Reasoning</span>
          </h1>

          <p className="hero-description">
            Query the new Bharatiya Nyaya Sanhita (BNS), BNSS, and BSS provisions with sub-second hybrid vector search, cross-encoder re-ranking, and audit-ready statutory citations.
          </p>

          <div className="hero-actions">
            <button className="btn btn-primary btn-lg" onClick={onGetStarted}>
              Enter Legal Workspace →
            </button>
            <button className="btn btn-secondary btn-lg" onClick={onLearnMore}>
              Explore Architecture
            </button>
          </div>

          <div className="hero-stats">
            <div className="stat-item">
              <span className="stat-value">&lt;600ms</span>
              <span className="stat-label">End-to-End Latency</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">100%</span>
              <span className="stat-label">Statutory Grounding</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">BNS / BNSS</span>
              <span className="stat-label">2023 Statutory Corpus</span>
            </div>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-image-card">
            <img 
              src={ladyJusticeHero} 
              alt="Lady Justice Artwork representing Indian Statutory Intelligence" 
              className="hero-image"
            />
            <div className="hero-image-overlay">
              <div className="overlay-badge">
                <span className="icon">📜</span>
                <span>Deterministic Evidence Corpus</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
