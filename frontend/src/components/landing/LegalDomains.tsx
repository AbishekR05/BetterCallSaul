import React from 'react';
import './LegalDomains.css';

const domains = [
  {
    title: 'Criminal Defense & BNS',
    description: 'Comprehensive coverage of offenses against person and property under Bharatiya Nyaya Sanhita (BNS) 2023.',
    highlight: true
  },
  {
    title: 'Procedural Compliance & BNSS',
    description: 'Investigation, FIR registration, arrest rules, and trial procedures under Bharatiya Nagarik Suraksha Sanhita 2023.',
    highlight: false
  },
  {
    title: 'Evidence & Digital Forensics',
    description: 'Admissibility of electronic records, certificates, and primary/secondary evidence under BSS 2023.',
    highlight: false
  },
  {
    title: 'Constitutional & Rights',
    description: 'Statutory alignment with Fundamental Rights under Articles 20, 21, and 22 of the Constitution of India.',
    highlight: false
  },
  {
    title: 'Commercial & Economic Offenses',
    description: 'Financial crimes, breach of trust, cheating, and corporate fraud provisions under BNS 2023.',
    highlight: false
  },
  {
    title: 'Bail & Custody Framework',
    description: 'Navigating regular, anticipatory, and interim bail applications under new BNSS provisions.',
    highlight: true
  },
  {
    title: 'Appellate & Revision Strategy',
    description: 'Appeals, revisions, and inherent High Court powers under BNSS Section 528.',
    highlight: false
  },
  {
    title: 'IPC to BNS Statutory Bridge',
    description: 'Instant cross-referencing between legacy Indian Penal Code sections and corresponding 2023 BNS clauses.',
    highlight: false
  }
];

export const LegalDomains: React.FC = () => {
  return (
    <section id="domains" className="domains-editorial-section">
      <div className="container">
        <div className="domains-header">
          <span className="section-eyebrow">Practice Areas</span>
          <h2 className="section-title font-serif">Explore 8 Specialized Legal Domains</h2>
          <p className="section-subtitle">
            Engineered to cover every dimension of modern Indian criminal law, procedure, and statutory evidence.
          </p>
        </div>

        <div className="domains-asymmetric-grid">
          {domains.map((domain, index) => (
            <div 
              key={index} 
              className={`domain-editorial-card ${domain.highlight ? 'featured-orange' : ''}`}
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
