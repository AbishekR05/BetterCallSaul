import React from 'react';
import './LegalDomains.css';

const domains = [
  {
    icon: '⚖️',
    title: 'Criminal Defense & BNS',
    description: 'Comprehensive coverage of offenses against person and property under Bharatiya Nyaya Sanhita (BNS) 2023.',
    topics: ['BNS §103 Murder', 'BNS §105 Homicide', 'BNS §303 Theft', 'BNS §111 Organized Crime']
  },
  {
    icon: '🚓',
    title: 'Procedural Compliance & BNSS',
    description: 'Investigation, FIR registration, arrest rules, and trial procedures under Bharatiya Nagarik Suraksha Sanhita 2023.',
    topics: ['BNSS §173 Zero FIR', 'BNSS §187 Custody', 'BNSS §482 Bail', 'BNSS §223 Cognizance']
  },
  {
    icon: '💾',
    title: 'Evidence & Digital Forensics',
    description: 'Admissibility of electronic records, certificates, and primary/secondary evidence under BSS 2023.',
    topics: ['BSS §63 Electronic Records', 'BSS §57 Primary Evidence', 'BSS §24 Admissions']
  },
  {
    icon: '🏛️',
    title: 'Constitutional & Rights',
    description: 'Statutory alignment with Fundamental Rights under Articles 20, 21, and 22 of the Constitution of India.',
    topics: ['Article 21 Rights', 'Double Jeopardy', 'Self-Incrimination', 'Legal Aid']
  },
  {
    icon: '💼',
    title: 'Commercial & Economic Offenses',
    description: 'Financial crimes, breach of trust, cheating, and corporate fraud provisions under BNS 2023.',
    topics: ['BNS §316 Breach of Trust', 'BNS §318 Cheating', 'Forgery §336', 'Money Laundering']
  },
  {
    icon: '🔒',
    title: 'Bail & Custody Framework',
    description: 'Navigating regular, anticipatory, and interim bail applications under new BNSS provisions.',
    topics: ['Anticipatory Bail §482', 'Default Bail §187', 'Bail Bonds', 'Surety Verification']
  },
  {
    icon: '📑',
    title: 'Appellate & Revision Strategy',
    description: 'Appeals, revisions, and inherent High Court powers under BNSS Section 528.',
    topics: ['BNSS §528 Inherent Powers', 'High Court Revisions', 'SLP Appeals', 'Sentence Suspension']
  },
  {
    icon: '🔄',
    title: 'IPC to BNS Statutory Bridge',
    description: 'Instant cross-referencing between legacy Indian Penal Code sections and corresponding 2023 BNS clauses.',
    topics: ['IPC §302 → BNS §103', 'IPC §420 → BNS §318', 'IPC §376 → BNS §64', 'IPC §498A → BNS §85']
  }
];

export const LegalDomains: React.FC = () => {
  return (
    <section id="domains" className="domains-section">
      <div className="container">
        <div className="domains-header">
          <span className="section-badge">JURISPRUDENCE SCOPE</span>
          <h2 className="section-title">Explore 8 Specialized Legal Domains</h2>
          <p className="section-subtitle">
            Engineered to cover every dimension of modern Indian criminal law, procedure, and statutory evidence.
          </p>
        </div>

        <div className="domains-grid">
          {domains.map((domain, index) => (
            <div key={index} className="domain-card">
              <div className="domain-icon">{domain.icon}</div>
              <h3>{domain.title}</h3>
              <p>{domain.description}</p>
              <div className="domain-topics">
                {domain.topics.map((t, idx) => (
                  <span key={idx} className="topic-tag">{t}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default LegalDomains;
