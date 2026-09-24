import React from 'react';
import './Values.css';

const values = [
  {
    num: '01',
    title: 'Deterministic Grounding',
    description: 'Every answer is strictly constrained to official statutory text. No hallucinated legal sections or arbitrary interpretations.'
  },
  {
    num: '02',
    title: 'Sub-Second Latency',
    description: 'Engineered with Phase 3.0 vector indexing and Phase 3.1 rate limiting for <600ms end-to-end response generation.'
  },
  {
    num: '03',
    title: 'Audit-Ready Citations',
    description: 'Every legal argument includes explicit statutory section tags and an interactive statutory evidence drawer.'
  },
  {
    num: '04',
    title: 'Cryptographic Security',
    description: 'JWT tokens hashed via SHA-256 at rest, request rate-limiting, and sanitized DOMPurify XSS protections.'
  }
];

export const Values: React.FC = () => {
  return (
    <section id="values" className="values-editorial-section">
      <div className="container">
        <div className="values-header">
          <span className="section-eyebrow">Our Value</span>
          <h2 className="section-title font-serif">Built for Precision in Litigation</h2>
          <p className="section-subtitle">
            Unwavering legal accuracy engineered specifically for Indian criminal and statutory jurisprudence.
          </p>
        </div>

        <div className="values-grid">
          {values.map((v, i) => (
            <div key={i} className="value-card-text">
              <span className="value-num font-serif">{v.num}</span>
              <h3 className="value-card-title font-serif">{v.title}</h3>
              <p className="value-card-desc">{v.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Values;
