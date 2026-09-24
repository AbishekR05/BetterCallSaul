import React from 'react';
import './Plans.css';

interface PlansProps {
  onSelectPlan: () => void;
}

export const Plans: React.FC<PlansProps> = ({ onSelectPlan }) => {
  return (
    <section id="plans" className="plans-section">
      <div className="container">
        <div className="plans-header">
          <span className="section-badge">TRANSPARENT TIERS</span>
          <h2 className="section-title">Designed for Counsel & Enterprise</h2>
          <p className="section-subtitle">
            Scale statutory search and intelligence across independent practice or law firm teams.
          </p>
        </div>

        <div className="plans-grid">
          {/* Free Tier */}
          <div className="plan-card">
            <div className="plan-header">
              <h3 className="plan-name">Independent Counsel</h3>
              <div className="plan-price">
                <span className="amount">₹0</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For advocates and legal researchers needing fast BNS/BNSS statutory lookups.</p>
            </div>

            <ul className="plan-features">
              <li><span className="check">✓</span> 50 Statutory queries / month</li>
              <li><span className="check">✓</span> BNS, BNSS & BSS provision indexing</li>
              <li><span className="check">✓</span> Hybrid semantic vector search</li>
              <li><span className="check">✓</span> Interactive statutory evidence drawer</li>
              <li><span className="check">✓</span> Sub-second latency responses</li>
            </ul>

            <button className="btn btn-secondary plan-btn" onClick={onSelectPlan}>
              Get Started Free
            </button>
          </div>

          {/* Pro / Enterprise Tier */}
          <div className="plan-card featured">
            <div className="plan-badge">MOST POPULAR</div>
            <div className="plan-header">
              <h3 className="plan-name">Chambers & Litigation</h3>
              <div className="plan-price">
                <span className="amount">₹4,999</span>
                <span className="period">/ month</span>
              </div>
              <p className="plan-desc">For litigation firms requiring unlimited statutory analysis and audit exports.</p>
            </div>

            <ul className="plan-features">
              <li><span className="check">✓</span> Unlimited Statutory queries</li>
              <li><span className="check">✓</span> Full BNS, BNSS, BSS & IPC mapping</li>
              <li><span className="check">✓</span> High-priority re-ranking pipeline</li>
              <li><span className="check">✓</span> Multi-turn session persistence</li>
              <li><span className="check">✓</span> Export audit-ready statutory briefs</li>
              <li><span className="check">✓</span> Dedicated support & SLA guarantees</li>
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
