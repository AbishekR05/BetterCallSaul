import React, { useState } from 'react';
import './Navbar.css';

interface NavbarProps {
  onOpenLogin: () => void;
  onOpenRegister: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenLogin, onOpenRegister }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="hero-navbar" aria-label="Main Navigation">
      <div className="hero-navbar-container">
        {/* Scale of Justice SVG Logo */}
        <a href="#" className="hero-navbar-brand">
          <svg className="scale-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <path d="M12 3v18M4 7h16M4 7l4 8M12 7l-4 8M12 7l4 8M20 7l-4 8M2 15h8M14 15h8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="brand-name font-serif">BetterCallSaul</span>
        </a>

        {/* Links */}
        <div className={`hero-navbar-links ${mobileMenuOpen ? 'active' : ''}`}>
          <a href="#about" onClick={() => setMobileMenuOpen(false)}>About us</a>
          <a href="#domains" onClick={() => setMobileMenuOpen(false)}>Practice Areas</a>
          <a href="#values" onClick={() => setMobileMenuOpen(false)}>Our Value</a>
          <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)}>Workflow</a>
          <a href="#plans" onClick={() => setMobileMenuOpen(false)}>Pricing</a>
        </div>

        {/* Action Buttons */}
        <div className="hero-navbar-actions">
          <button className="nav-sign-in-btn" onClick={onOpenLogin}>
            Sign In
          </button>
          <button className="btn btn-outline-white nav-consult-btn" onClick={onOpenRegister}>
            Launch Workspace <span className="arrow-icon">↗</span>
          </button>

          <button 
            className="mobile-menu-toggle"
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
