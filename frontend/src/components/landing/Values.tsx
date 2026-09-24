import React from 'react';
import './Values.css';

const values = [
  {
    num: '01',
    title: '100% Accurate & Verified',
    description: 'Every answer comes directly from official law books. No made-up laws or false sections.'
  },
  {
    num: '02',
    title: 'Instant Search Results',
    description: 'Find relevant legal sections and clear explanations in less than a second.'
  },
  {
    num: '03',
    title: 'Clear Legal Sources',
    description: 'Every answer shows the exact act, section, and law reference so you can verify it yourself.'
  },
  {
    num: '04',
    title: 'Private & Secure',
    description: 'Your search history and questions are encrypted and kept strictly confidential.'
  }
];

export const Values: React.FC = () => {
  return (
    <section id="values" className="values-editorial-section">
      <div className="container">
        <div className="values-header">
          <span className="section-eyebrow">Our Value</span>
          <h2 className="section-title font-serif">Why You Can Trust BetterCallSaul</h2>
          <p className="section-subtitle">
            Clear, accurate legal guidance designed for everyone.
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
