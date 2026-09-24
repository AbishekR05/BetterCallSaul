import React from 'react';
import './FinalCTA.css';

interface FinalCTAProps {
  onGetStarted: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onGetStarted }) => {
  return (
    <section className="cta-editorial-section">
      <div className="container">
        <div className="cta-warm-card">
          <div className="cta-inner-content">
            <h2 className="cta-title font-serif">Ready to Get Instant Legal Answers?</h2>
            <p className="cta-description">
              Search new Indian laws, compare old and new penal sections, and get verified legal guidance in seconds.
            </p>
            <div className="cta-actions">
              <button className="btn btn-white cta-btn" onClick={onGetStarted}>
                Launch Legal Workspace <span>↗</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FinalCTA;
