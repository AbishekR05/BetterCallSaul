import React from 'react';
import './FinalCTA.css';

interface FinalCTAProps {
  onGetStarted: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onGetStarted }) => {
  return (
    <section className="cta-section">
      <div className="container">
        <div className="cta-box">
          <div className="cta-content">
            <h2 className="cta-title">Ready to Elevate Your Legal Research?</h2>
            <p className="cta-description">
              Query statutory provisions, cross-reference new penal codes (BNS, BNSS, BSS), and obtain grounded citations in sub-second latency.
            </p>
            <div className="cta-actions">
              <button className="btn btn-primary btn-lg" onClick={onGetStarted}>
                Launch Legal Workspace →
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FinalCTA;
