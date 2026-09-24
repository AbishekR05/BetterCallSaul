import React from 'react';
import legalAbstractBg from '../../assets/legal_abstract_bg.jpg';
import './About.css';

export const About: React.FC = () => {
  return (
    <section id="about" className="about-section">
      <div className="container about-grid">
        <div className="about-visual">
          <div className="about-image-card">
            <img 
              src={legalAbstractBg} 
              alt="Statutory law book abstract" 
              className="about-image" 
            />
            <div className="about-card-badge">
              <span>BNS • BNSS • BSS 2023</span>
            </div>
          </div>
        </div>

        <div className="about-content">
          <span className="section-badge">SYSTEM OVERVIEW</span>
          <h2 className="section-title">Bridging Legacy Penal Codes with 2023 Statutory Reform</h2>
          <p className="about-text">
            On July 1, 2024, India enforced the Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Sanhita (BSS), replacing the 160-year-old IPC, CrPC, and Indian Evidence Act.
          </p>
          <p className="about-text">
            <strong>BetterCallSaul</strong> provides advocates, legal researchers, and judicial clerks with an intelligent, audit-ready reasoning engine. It translates statutory queries across both legacy and new frameworks with exact legal citation backing.
          </p>

          <div className="about-features-list">
            <div className="feature-item">
              <span className="feature-icon">🔍</span>
              <div>
                <h4>Hybrid Semantic Search</h4>
                <p>Combines dense vector embeddings with BM25 keyword matching across all statutory provisions.</p>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-icon">🛡️</span>
              <div>
                <h4>Hallucination Protection</h4>
                <p>LLM responses are bound strictly to retrieved statutory provisions with evidence citations.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default About;
