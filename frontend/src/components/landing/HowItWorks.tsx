import React from 'react';
import './HowItWorks.css';

const steps = [
  {
    num: '01',
    title: 'Ask Your Question',
    description: 'Type any legal query or question in plain English or section numbers.'
  },
  {
    num: '02',
    title: 'Search Official Laws',
    description: 'Our engine scans official databases of India\'s new criminal laws (BNS, BNSS, BSS).'
  },
  {
    num: '03',
    title: 'Find Relevant Sections',
    description: 'The system identifies the exact penal sections and provisions matching your query.'
  },
  {
    num: '04',
    title: 'Explain in Plain English',
    description: 'Complex legal jargon is converted into clear, easy-to-read explanations.'
  },
  {
    num: '05',
    title: 'Show Exact Sources',
    description: 'View original legal clauses and section numbers for complete verification.'
  }
];

export const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="how-editorial-dark-band">
      <div className="container">
        <div className="how-header">
          <span className="section-eyebrow light">Workflow</span>
          <h2 className="section-title font-serif text-white">How BetterCallSaul Works in 5 Simple Steps</h2>
          <p className="section-subtitle text-light">
            A reliable, step-by-step process to give you verified legal answers.
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
