import React from 'react';
import legalAbstractBg from '../../assets/legal_abstract_bg.jpg';
import './About.css';

export const About: React.FC = () => {
  return (
    <section id="about" className="about-editorial-section">
      <div className="container about-grid">
        
        {/* Single Featured Balance & Statutory Image Card */}
        <div className="about-visual-card">
          <img 
            src={legalAbstractBg} 
            alt="Balance of justice and statutory law book" 
            className="about-img-featured" 
          />
        </div>

        {/* Text Content */}
        <div className="about-content-box">
          <span className="section-eyebrow">About us</span>
          <h2 className="section-title font-serif">
            Bridging Legacy Penal Codes with 2023 Statutory Reform
          </h2>
          <p className="about-paragraph">
            On July 1, 2024, India enforced the Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Sanhita (BSS), replacing the 160-year-old IPC, CrPC, and Indian Evidence Act.
          </p>
          <p className="about-paragraph highlight">
            BetterCallSaul provides advocates, legal researchers, and judicial clerks with an intelligent, audit-ready reasoning engine. It translates statutory queries across both legacy and new frameworks with exact legal citation backing.
          </p>

          <div className="about-metrics-row">
            <div className="about-metric">
              <span className="metric-val font-serif">100%</span>
              <span className="metric-desc">Grounded in verified BNS &amp; BNSS provisions</span>
            </div>
            <div className="about-metric">
              <span className="metric-val font-serif">&lt;600ms</span>
              <span className="metric-desc">End-to-end vector retrieval latency</span>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default About;
