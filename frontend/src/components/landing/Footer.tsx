import React from 'react';
import './Footer.css';

export const Footer: React.FC = () => {
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, targetId: string) => {
    e.preventDefault();
    if (targetId === 'top') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    const element = document.getElementById(targetId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="footer-editorial">
      <div className="container">
        <div className="footer-top">
          <div className="footer-brand font-serif">
            <a 
              href="#top" 
              className="footer-logo"
              onClick={(e) => handleNavClick(e, 'top')}
            >
              <svg className="footer-scale-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                <path d="M12 3v18M4 7h16M4 7l4 8M12 7l-4 8M12 7l4 8M20 7l-4 8M2 15h8M14 15h8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span className="logo-text">BetterCallSaul</span>
            </a>
            <p className="footer-tagline font-sans">
              Deterministic, audit-ready Indian statutory retrieval &amp; grounded reasoning platform.
            </p>
          </div>

          <div className="footer-links font-sans">
            <div className="footer-col">
              <h4>Navigation</h4>
              <a href="#about" onClick={(e) => handleNavClick(e, 'about')}>About us</a>
              <a href="#values" onClick={(e) => handleNavClick(e, 'values')}>Our Value</a>
              <a href="#domains" onClick={(e) => handleNavClick(e, 'domains')}>Practice Areas</a>
              <a href="#how-it-works" onClick={(e) => handleNavClick(e, 'how-it-works')}>Workflow</a>
              <a href="#plans" onClick={(e) => handleNavClick(e, 'plans')}>Pricing</a>
            </div>

            <div className="footer-col">
              <h4>Statutory Framework</h4>
              <a href="#domains" onClick={(e) => handleNavClick(e, 'domains')}>BNS 2023</a>
              <a href="#domains" onClick={(e) => handleNavClick(e, 'domains')}>BNSS 2023</a>
              <a href="#domains" onClick={(e) => handleNavClick(e, 'domains')}>BSS 2023</a>
              <a href="#domains" onClick={(e) => handleNavClick(e, 'domains')}>IPC Bridge Map</a>
            </div>
          </div>
        </div>

        <div className="footer-disclaimer-box font-sans">
          <p className="footer-disclaimer">
            <strong>Legal Disclaimer:</strong> BetterCallSaul is an AI statutory research assistant, not a licensed advocate; statutory interpretations require verification by qualified legal counsel under the Advocates Act, 1961.
          </p>
        </div>

        <div className="footer-bottom font-sans">
          <p>© {new Date().getFullYear()} BetterCallSaul Legal Intelligence. All rights reserved.</p>
          <div className="footer-meta">
            <span>Phase 3.2 Production Release</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
