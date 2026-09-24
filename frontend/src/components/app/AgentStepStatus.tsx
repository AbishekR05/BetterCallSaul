import React, { useEffect, useState } from 'react';
import './AgentStepStatus.css';

export type StepState = 'understanding' | 'searching' | 'checking_evidence' | 'preparing_response';

interface AgentStepStatusProps {
  currentStep: StepState;
}

const stepsConfig: { key: StepState; label: string; detail: string }[] = [
  {
    key: 'understanding',
    label: 'Understanding Legal Intent',
    detail: 'Parsing query, extracting penal section entities & jurisdictions'
  },
  {
    key: 'searching',
    label: 'Searching Statutory Corpus',
    detail: 'Executing hybrid vector dense retrieval & sparse BM25 keyword matching'
  },
  {
    key: 'checking_evidence',
    label: 'Checking Statutory Evidence',
    detail: 'Applying cross-encoder re-ranking & validating statutory provisions'
  },
  {
    key: 'preparing_response',
    label: 'Synthesizing Grounded Answer',
    detail: 'Formulating plain-English response with exact statutory citations'
  }
];

export const AgentStepStatus: React.FC<AgentStepStatusProps> = ({ currentStep }) => {
  const [elapsedMs, setElapsedMs] = useState<number>(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      setElapsedMs(Date.now() - startTime);
    }, 50);

    return () => clearInterval(interval);
  }, [currentStep]);

  const currentIndex = stepsConfig.findIndex(s => s.key === currentStep);

  return (
    <div className="agent-step-container">
      <div className="agent-step-header">
        <div className="agent-title">
          <span className="agent-spinner"></span>
          <span>Reasoning Pipeline Active</span>
        </div>
        <div className="agent-timer">
          {(elapsedMs / 1000).toFixed(2)}s
        </div>
      </div>

      <div className="agent-steps-list">
        {stepsConfig.map((step, idx) => {
          let status: 'completed' | 'active' | 'pending' = 'pending';
          if (idx < currentIndex) status = 'completed';
          else if (idx === currentIndex) status = 'active';

          return (
            <div key={step.key} className={`step-item ${status}`}>
              <div className="step-indicator">
                {status === 'completed' ? (
                  <span className="step-check">✓</span>
                ) : status === 'active' ? (
                  <span className="step-pulse"></span>
                ) : (
                  <span className="step-dot"></span>
                )}
              </div>
              <div className="step-details">
                <div className="step-label">{step.label}</div>
                {status === 'active' && (
                  <div className="step-subdetail">{step.detail}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
