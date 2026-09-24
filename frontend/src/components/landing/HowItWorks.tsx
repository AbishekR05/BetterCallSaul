import React from 'react';
import './HowItWorks.css';

const steps = [
  {
    num: '01',
    title: 'Query Processing & Intent',
    description: 'System normalizes query, extracts statutory entities, and structures multi-jurisdictional parameters.'
  },
  {
    num: '02',
    title: 'Hybrid Vector Retrieval',
    description: 'Queries BNS/BNSS/BSS vector indexes using dense semantic embeddings alongside BM25 sparse matching.'
  },
  {
    num: '03',
    title: 'Cross-Encoder Re-Ranking',
    description: 'Top candidate provisions are re-ranked through a cross-encoder model to maximize precision.'
  },
  {
    num: '04',
    title: 'Grounded Synthesis',
    description: 'LLM generates plain-English legal explanations strictly bound by retrieved statutory provisions.'
  },
  {
    num: '05',
    title: 'Citation Audit',
    description: 'Every statement is dynamically cross-referenced against raw statutory text in the evidence drawer.'
  }
];

export const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="how-editorial-dark-band">
      <div className="container">
        <div className="how-header">
          <span className="section-eyebrow light">Workflow</span>
          <h2 className="section-title font-serif text-white">How BetterCallSaul Operates</h2>
          <p className="section-subtitle text-light">
            A 5-stage deterministic pipeline engineered to deliver audit-ready Indian statutory intelligence.
          </p>
        </div>

        <div className="steps-row">
          {steps.map((step, index) => (
            <div key={index} className="step-col">
              <span className="step-num font-serif">{step.num}</span>
              <h3 className="step-title font-serif">{step.title}</h3>
              <p className="step-desc">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
