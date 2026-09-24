import React from 'react';
import ladyJusticeHero from '../../assets/lady_justice_hero.jpg';
import advocatePortrait from '../../assets/advocate_portrait.jpg';
import './Hero.css';

interface HeroProps {
  onGetStarted: () => void;
  onLearnMore: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted }) => {
  return (
    <section className="hero-dark-frame">
      <div className="hero-inner-container">
        
        {/* Top Header Paragraph Row */}
        <div className="hero-top-row">
          <div className="hero-text-right">
            <p className="hero-paragraph">
              Need instant statutory intelligence? Query BNS, BNSS &amp; BSS provisions with grounded hybrid vector search and audit-ready legal citations.
            </p>
          </div>
        </div>

        {/* Center Spotlight & Lady Justice Artwork */}
        <div className="hero-center-visual">
          <img 
            src={ladyJusticeHero} 
            alt="Lady Justice Statue Artwork" 
            className="hero-statue-img"
          />
          <div className="hero-spotlight-overlay"></div>
        </div>

        {/* Bottom Headline, Button & Overlapping Stat Card Row */}
        <div className="hero-bottom-row">
          <div className="hero-headline-left">
            <h1 className="hero-main-title font-serif">
              Justice Should Be<br />Everyone,<br />Without Fear
            </h1>
            <button className="btn btn-white hero-cta-btn" onClick={onGetStarted}>
              Launch Workspace <span className="arrow">↗</span>
            </button>
          </div>

          {/* Floating White Card */}
          <div className="hero-card-right">
            <div className="card-top-content">
              {/* Avatar Stack */}
              <div className="avatar-stack">
                <div className="avatar-circle av-1">A</div>
                <div className="avatar-circle av-2">R</div>
                <div className="avatar-circle av-3">S</div>
              </div>
              <div className="card-stat font-serif">152k+</div>
              <div className="card-stat-label">Statutory Searches</div>
            </div>

            {/* Portrait Thumbnail */}
            <div className="card-photo-wrapper">
              <img 
                src={advocatePortrait} 
                alt="Advocate researching in law library" 
                className="card-photo" 
              />
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
