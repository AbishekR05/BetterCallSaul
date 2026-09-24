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
          <h2 className="section-title font-serif">Designed for Counsel &amp; Enterprise</h2>
          <p className="section-subtitle">
            Scale statutory search and intelligence across independent practice or law firm teams.
          </p>
        </div>

        <div className="plans-grid">
          {/* Free Tier Card */}
          <div className="plan-card light-tone">
            <div className="plan-header">
              <h3 className="plan-name font-serif">Independent Counsel</h3>
              <div className="plan-price">
                <span className="amount font-serif">₹0</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For advocates and legal researchers needing fast BNS/BNSS statutory lookups.</p>
            </div>

            <ul className="plan-features">
              <li><span className="tick-icon">✓</span> 50 Statutory queries / month</li>
              <li><span className="tick-icon">✓</span> BNS, BNSS &amp; BSS provision indexing</li>
              <li><span className="tick-icon">✓</span> Hybrid semantic vector search</li>
              <li><span className="tick-icon">✓</span> Interactive statutory evidence drawer</li>
              <li><span className="tick-icon">✓</span> Sub-second latency responses</li>
            </ul>

            <button className="btn btn-secondary plan-btn" onClick={onSelectPlan}>
              Get Started Free
            </button>
          </div>

          {/* Pro Tier Card - Two Tone Dark Contrast */}
          <div className="plan-card dark-tone">
            <div className="plan-badge-pill">MOST POPULAR</div>
            <div className="plan-header">
              <h3 className="plan-name font-serif">Chambers &amp; Litigation</h3>
              <div className="plan-price">
                <span className="amount font-serif">₹4,999</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For litigation firms requiring unlimited statutory analysis and audit exports.</p>
            </div>

            <ul className="plan-features">
              <li><span className="tick-icon orange">✓</span> Unlimited Statutory queries</li>
              <li><span className="tick-icon orange">✓</span> Full BNS, BNSS, BSS &amp; IPC mapping</li>
              <li><span className="tick-icon orange">✓</span> High-priority re-ranking pipeline</li>
              <li><span className="tick-icon orange">✓</span> Multi-turn session persistence</li>
              <li><span className="tick-icon orange">✓</span> Export audit-ready statutory briefs</li>
              <li><span className="tick-icon orange">✓</span> Dedicated support &amp; SLA guarantees</li>
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
