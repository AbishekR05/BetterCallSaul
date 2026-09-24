import React from 'react';
import './Plans.css';

interface PlansProps {
  onSelectPlan: () => void;
}

export const Plans: React.FC<PlansProps> = ({ onSelectPlan }) => {
  return (
    <section id="plans" className="plans-editorial-section">
      <div className="container">
        <div className="plans-header">
          <span className="section-eyebrow">Pricing</span>
          <h2 className="section-title font-serif">Simple Plans for Everyone</h2>
          <p className="section-subtitle">
            Choose the option that best fits your legal research needs.
          </p>
        </div>

        <div className="plans-grid">
          {/* Free Tier Card */}
          <div className="plan-card light-tone">
            <div className="plan-header">
              <h3 className="plan-name font-serif">Basic Access</h3>
              <div className="plan-price">
                <span className="amount font-serif">₹0</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For individuals, advocates, and students needing quick law searches.</p>
            </div>

            <ul className="plan-features">
              <li><span className="tick-icon">✓</span> 50 Legal queries / month</li>
              <li><span className="tick-icon">✓</span> Search BNS, BNSS &amp; BSS laws</li>
              <li><span className="tick-icon">✓</span> Plain-English legal explanations</li>
              <li><span className="tick-icon">✓</span> View official section sources</li>
              <li><span className="tick-icon">✓</span> Fast response time</li>
            </ul>

            <button className="btn btn-secondary plan-btn" onClick={onSelectPlan}>
              Get Started Free
            </button>
          </div>

          {/* Pro Tier Card - Two Tone Dark Contrast */}
          <div className="plan-card dark-tone">
            <div className="plan-badge-pill">MOST POPULAR</div>
            <div className="plan-header">
              <h3 className="plan-name font-serif">Chambers &amp; Professional</h3>
              <div className="plan-price">
                <span className="amount font-serif">₹4,999</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For legal chambers, advocates, and law firms needing unlimited searches.</p>
            </div>

            <ul className="plan-features">
              <li><span className="tick-icon orange">✓</span> Unlimited Legal queries</li>
              <li><span className="tick-icon orange">✓</span> Complete old IPC to new BNS mapping</li>
              <li><span className="tick-icon orange">✓</span> High-speed priority engine</li>
              <li><span className="tick-icon orange">✓</span> Multi-turn research history</li>
              <li><span className="tick-icon orange">✓</span> Export audit-ready legal summaries</li>
              <li><span className="tick-icon orange">✓</span> Dedicated support</li>
            </ul>

            <button className="btn btn-primary plan-btn" onClick={onSelectPlan}>
              Access Professional
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Plans;
