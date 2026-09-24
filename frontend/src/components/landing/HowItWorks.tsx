import React from 'react';
import './HowItWorks.css';

const steps = [
  {
    num: '01',
    title: 'Query Processing & Intent',
    description: 'The system normalizes your query, extracts statutory entities, and structures multi-jurisdictional retrieval parameters.'
  },
  {
    num: '02',
    title: 'Hybrid Vector Retrieval',
    description: 'Queries BNS/BNSS/BSS vector indexes using dense semantic embeddings alongside BM25 sparse lexical matching.'
  },
  {
    num: '03',
    title: 'Cross-Encoder Re-Ranking',
    description: 'Top candidate provisions are re-ranked through a cross-encoder model to maximize contextual precision and eliminate noise.'
  },
  {
    num: '04',
    title: 'Grounded Synthesis',
    description: 'LLM generates plain-English legal explanations strictly bound by retrieved statutory provisions, avoiding hallucinated clauses.'
  },
  {
    num: '05',
    title: 'Citation Audit & Verification',
    description: 'Every statement is dynamically cross-referenced against the raw BNS/BNSS/BSS statutory text with interactive evidence drawer.'
  }
];

export const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="how-it-works-section">
      <div className="container">
        <div className="how-header">
          <span className="section-badge">ARCHITECTURE & WORKFLOW</span>
          <h2 className="section-title">How BetterCallSaul Operates</h2>
          <p className="section-subtitle">
            A 5-stage deterministic pipeline engineered to deliver audit-ready, hallucination-free Indian statutory intelligence.
          </p>
        </div>

        <div className="steps-container">
          <div className="steps-line"></div>
          {steps.map((step, index) => (
            <div key={index} className="step-card">
              <div className="step-number-container">
                <div className="step-number">{step.num}</div>
              </div>
              <div className="step-content">
                <h3 className="step-title">{step.title}</h3>
                <p className="step-desc">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
