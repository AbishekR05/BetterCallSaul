import React from 'react';
import { Citation } from '../../api/turnsApi';
import './EvidencePanel.css';

interface EvidencePanelProps {
  isOpen: boolean;
  onClose: () => void;
  citations: Citation[];
  selectedCitationIndex?: number | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  isOpen,
  onClose,
  citations,
  selectedCitationIndex = null
}) => {
  if (!isOpen) return null;

  return (
    <aside className="evidence-drawer" aria-label="Statutory Evidence Drawer">
      <div className="drawer-header">
        <div className="drawer-title-group">
          <svg className="drawer-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
          </svg>
          <h3 className="drawer-title font-serif">Statutory Evidence Corpus</h3>
        </div>
        <button className="drawer-close-btn" onClick={onClose} aria-label="Close evidence panel">
          ✕
        </button>
      </div>

      <div className="drawer-body">
        {citations.length === 0 ? (
          <div className="empty-evidence">
            <p>No statutory citations retrieved for this message turn.</p>
          </div>
        ) : (
          <div className="citations-list">
            {citations.map((cit, idx) => {
              const isSelected = selectedCitationIndex === idx;
              const sectionLabel = `${cit.document_title} ${cit.section ? '§' + cit.section : ''}`;

              return (
                <div key={idx} className={`citation-card ${isSelected ? 'selected' : ''}`}>
                  <div className="citation-badge">
                    <span className="act-tag">{cit.document_type || 'Statute'}</span>
                    {cit.jurisdiction && <span className="section-tag">{cit.jurisdiction}</span>}
                    {cit.section && <span className="section-tag">Sec {cit.section}</span>}
                  </div>

                  <h4 className="citation-title font-serif">
                    {sectionLabel}
                  </h4>

                  <div className="citation-text">
                    {cit.source_reference || `Official provision excerpt under ${cit.document_title}`}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="drawer-footer">
        <span>Verified against Ministry of Law &amp; Justice BNS/BNSS/BSS Corpus</span>
      </div>
    </aside>
  );
};

export default EvidencePanel;
