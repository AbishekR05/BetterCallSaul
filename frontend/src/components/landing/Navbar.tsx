import React, { useState } from 'react';
import './Navbar.css';

interface NavbarProps {
  onOpenLogin: () => void;
  onOpenRegister: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenLogin, onOpenRegister }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="navbar" aria-label="Main Navigation">
      <div className="container navbar-container">
        <a href="#" className="navbar-brand">
          <span className="brand-icon">⚖️</span>
          <span className="brand-text">BetterCallSaul</span>
          <span className="brand-tag">Phase 3.2</span>
        </a>

        <div className={`navbar-links ${mobileMenuOpen ? 'active' : ''}`}>
          <a href="#about" onClick={() => setMobileMenuOpen(false)}>About</a>
          <a href="#values" onClick={() => setMobileMenuOpen(false)}>Core Values</a>
          <a href="#domains" onClick={() => setMobileMenuOpen(false)}>Legal Domains</a>
          <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)}>Architecture</a>
          <a href="#plans" onClick={() => setMobileMenuOpen(false)}>Pricing</a>
        </div>

        <div className="navbar-actions">
          <button className="btn btn-secondary" onClick={onOpenLogin}>
            Sign In
          </button>
          <button className="btn btn-primary" onClick={onOpenRegister}>
            Launch Workspace
          </button>

          <button 
            className="mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
