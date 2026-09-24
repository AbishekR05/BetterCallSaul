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
            Understand India’s New Legal System with Ease
          </h2>
          <p className="about-paragraph">
            In 2024, India updated its criminal laws, replacing the 160-year-old Indian Penal Code (IPC) with the new Bharatiya Nyaya Sanhita (BNS), BNSS, and BSS.
          </p>
          <p className="about-paragraph highlight">
            BetterCallSaul helps lawyers, students, and citizens search, compare, and understand both old and new legal sections instantly with verified statutory citations.
          </p>

          <div className="about-metrics-row">
            <div className="about-metric">
              <span className="metric-val font-serif">100%</span>
              <span className="metric-desc">Grounded in verified BNS &amp; BNSS provisions</span>
            </div>
            <div className="about-metric">
              <span className="metric-val font-serif">&lt;1 Sec</span>
              <span className="metric-desc">Instant, accurate legal answers</span>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default About;
