import React from 'react';
import ladyJusticeHero from '../../assets/lady_justice_hero.png';
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
        
        {/* Bottom Headline & Right-Aligned Supporting Card Row */}
        <div className="hero-bottom-row">
          {/* Main Headline Left */}
          <div className="hero-headline-left">
            <h1 className="hero-main-title font-serif">
              Justice Should Be<br />Accessible to Everyone,<br />Without Fear
            </h1>
            <button className="btn btn-white hero-cta-btn" onClick={onGetStarted}>
              Launch Workspace <span className="arrow">↗</span>
            </button>
          </div>

          {/* Supporting Card Right */}
          <div className="hero-supporting-card-bottom">
            <h3 className="card-badge-title font-serif">Grounded in Indian Law</h3>
            <p className="card-badge-text">
              Get clear answers backed by relevant legislation, judgments, and cited legal sources.
            </p>
          </div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
