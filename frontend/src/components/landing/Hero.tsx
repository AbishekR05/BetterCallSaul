import React from 'react';
import ladyJusticeHero from '../../assets/lady_justice_hero.jpg';
import './Hero.css';

interface HeroProps {
  onGetStarted: () => void;
  onLearnMore: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted }) => {
  return (
    <section className="hero-dark-frame">
      {/* Full-screen background image with subtle vignette overlay */}
      <div 
        className="hero-bg-cover"
        style={{ backgroundImage: `url(${ladyJusticeHero})` }}
      >
        <div className="hero-vignette-overlay"></div>
      </div>

      <div className="hero-inner-container">
        
        {/* Top Header Paragraph Row */}
        <div className="hero-top-row">
          <div className="hero-text-right">
            <p className="hero-paragraph">
              Need instant statutory intelligence? Query BNS, BNSS &amp; BSS provisions with grounded hybrid vector search and audit-ready legal citations.
            </p>
          </div>
        </div>

        {/* Bottom Headline & Action Button Row */}
        <div className="hero-bottom-row">
          <div className="hero-headline-left">
            <h1 className="hero-main-title font-serif">
              Justice Should Be<br />Everyone,<br />Without Fear
            </h1>
            <button className="btn btn-white hero-cta-btn" onClick={onGetStarted}>
              Launch Workspace <span className="arrow">↗</span>
            </button>
          </div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
