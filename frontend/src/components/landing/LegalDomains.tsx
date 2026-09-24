import React from 'react';
import './LegalDomains.css';

const domains = [
  {
    title: 'Criminal Defense & BNS',
    description: 'Understand laws covering crimes, penalties, and defense under the new Bharatiya Nyaya Sanhita (BNS) 2023.'
  },
  {
    title: 'Police & Court Procedures (BNSS)',
    description: 'Learn about FIR filing, police investigation, arrest rules, and court procedures under BNSS 2023.'
  },
  {
    title: 'Digital Evidence & Forensics',
    description: 'Rules for submitting electronic records, mobile evidence, and certificates in court under BSS 2023.'
  },
  {
    title: 'Constitutional Rights',
    description: 'Know your fundamental rights during arrest, questioning, and legal protection under Indian Law.'
  },
  {
    title: 'Financial & Business Fraud',
    description: 'Clear guidance on cheating, breach of trust, corporate fraud, and economic offenses.'
  },
  {
    title: 'Bail & Custody Framework',
    description: 'Understand how to apply for regular, anticipatory, and emergency bail under new laws.'
  },
  {
    title: 'Appeals & High Court Actions',
    description: 'How to appeal court decisions or request High Court intervention under new procedures.'
  },
  {
    title: 'Old IPC to New BNS Converter',
    description: 'Easily match old Indian Penal Code (IPC) section numbers to their new BNS counterparts.'
  }
];

export const LegalDomains: React.FC = () => {
  return (
    <section id="domains" className="domains-editorial-section">
      <div className="container">
        <div className="domains-header">
          <span className="section-eyebrow">Practice Areas</span>
          <h2 className="section-title font-serif">Explore 8 Legal Practice Areas</h2>
          <p className="section-subtitle">
            Simple, clear explanations across criminal law, court procedures, evidence, and your rights.
          </p>
        </div>

        <div className="domains-asymmetric-grid">
          {domains.map((domain, index) => (
            <div 
              key={index} 
              className="domain-editorial-card hover-orange"
            >
              <h3 className="domain-card-title font-serif">{domain.title}</h3>
              <p className="domain-card-desc">{domain.description}</p>
              <div className="domain-arrow-link">
                Learn more <span>↗</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default LegalDomains;
