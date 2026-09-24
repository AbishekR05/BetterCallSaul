import React from 'react';
import './Values.css';

const values = [
  {
    icon: '🎯',
    title: 'Deterministic Grounding',
    description: 'Every answer is strictly constrained to official statutory text. No hallucinated legal sections or arbitrary interpretations.'
  },
  {
    icon: '⚡',
    title: 'Sub-Second Latency',
    description: 'Engineered with Phase 3.0 vector indexing and Phase 3.1 rate limiting for <600ms end-to-end response generation.'
  },
  {
    icon: '📜',
    title: 'Audit-Ready Citations',
    description: 'Every legal argument includes explicit statutory section tags and an interactive statutory evidence drawer.'
  },
  {
    icon: '🔒',
    title: 'Cryptographic Security',
    description: 'JWT tokens hashed via SHA-256 at rest, request rate-limiting, and sanitized DOMPurify XSS protections.'
  }
];

export const Values: React.FC = () => {
  return (
    <section id="values" className="values-section">
      <div className="container">
        <div className="values-header">
          <span className="section-badge">CORE PRINCIPLES</span>
          <h2 className="section-title">Built for Precision in Litigation</h2>
          <p className="section-subtitle">
            Unwavering legal accuracy engineered specifically for Indian criminal and statutory jurisprudence.
          </p>
        </div>

        <div className="values-grid">
          {values.map((v, i) => (
            <div key={i} className="value-card">
              <div className="value-icon">{v.icon}</div>
              <h3 className="value-title">{v.title}</h3>
              <p className="value-desc">{v.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Values;
