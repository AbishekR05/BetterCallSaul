import React from 'react';
import './Footer.css';

export const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-top">
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="logo-icon">⚖️</span>
              <span className="logo-text">BetterCallSaul</span>
            </div>
            <p className="footer-tagline">
              Deterministic, audit-ready Indian statutory retrieval & grounded reasoning platform.
            </p>
          </div>

          <div className="footer-links">
            <div className="footer-col">
              <h4>Navigation</h4>
              <a href="#about">About System</a>
              <a href="#values">Core Values</a>
              <a href="#domains">Legal Domains</a>
              <a href="#how-it-works">Architecture</a>
              <a href="#plans">Pricing Tiers</a>
            </div>

            <div className="footer-col">
              <h4>Statutory Framework</h4>
              <a href="#domains">BNS 2023</a>
              <a href="#domains">BNSS 2023</a>
              <a href="#domains">BSS 2023</a>
              <a href="#domains">IPC Bridge Map</a>
            </div>
          </div>
        </div>

        <div className="footer-disclaimer-box">
          <p className="footer-disclaimer">
            <strong>Legal Disclaimer:</strong> BetterCallSaul is an AI statutory research assistant, not a licensed advocate; statutory interpretations require verification by qualified legal counsel under the Advocates Act, 1961.
          </p>
        </div>

        <div className="footer-bottom">
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
