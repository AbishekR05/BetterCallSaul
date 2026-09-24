import React, { useState, useEffect, useRef } from 'react';
import { turnsApi, Citation, GroundedAnswerResponse } from '../../api/turnsApi';
import { ApiError } from '../../api/client';
import { ChatMessage } from './ChatMessage';
import { AgentStepStatus, StepState } from './AgentStepStatus';
import { ErrorStateBanner } from './ErrorStateBanner';
import { EvidencePanel } from './EvidencePanel';
import './ChatWorkspace.css';

interface ChatWorkspaceProps {
  sessionId: string | null;
  sessionTitle?: string;
}

export interface DisplayTurn {
  turn_id: string;
  user_message: string;
  assistant_message: string;
  citations: Citation[];
  latency_ms?: number;
  timestamp: string;
}

const STARTER_PROMPTS = [
  {
    title: 'BNS Murder & Homicide Provisions',
    query: 'What is the statutory penalty for culpable homicide not amounting to murder under Bharatiya Nyaya Sanhita (BNS Section 105)?'
  },
  {
    title: 'BNSS Anticipatory Bail & Arrest',
    query: 'Explain the procedure for anticipatory bail under BNSS Section 482 compared to Section 438 of the old CrPC.'
  },
  {
    title: 'Zero FIR & Electronic Information',
    query: 'How does BNSS Section 173 govern the registration of Zero FIR and electronic FIR submissions?'
  },
  {
    title: 'Bharatiya Sakshya Sanhita Electronic Evidence',
    query: 'What are the certificate requirements for admissibility of electronic records under BSS Section 63?'
  }
];

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({ sessionId, sessionTitle }) => {
  const [messages, setMessages] = useState<DisplayTurn[]>([]);
  const [prompt, setPrompt] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<StepState>('understanding');
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState<boolean>(false);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [selectedCitationIdx, setSelectedCitationIdx] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Clear messages on session change
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [sessionId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing, error]);

  const handleSubmit = async (queryText?: string) => {
    const textToSubmit = queryText || prompt;
    if (!textToSubmit.trim() || !sessionId || isProcessing) return;

    setError(null);
    setPrompt('');
    setIsProcessing(true);

    const tempTurnId = `turn-${Date.now()}`;
    const startTime = Date.now();

    // Push optimistic user message
    const tempUserMsg: DisplayTurn = {
      turn_id: tempTurnId,
      user_message: textToSubmit,
      assistant_message: '',
      citations: [],
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    // Simulated reasoning pipeline steps
    setCurrentStep('understanding');
    const stepTimer1 = setTimeout(() => setCurrentStep('searching'), 300);
    const stepTimer2 = setTimeout(() => setCurrentStep('checking_evidence'), 700);
    const stepTimer3 = setTimeout(() => setCurrentStep('preparing_response'), 1100);

    try {
      const res: GroundedAnswerResponse = await turnsApi.postTurn(sessionId, textToSubmit);
      const elapsed = Date.now() - startTime;

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      const completedTurn: DisplayTurn = {
        turn_id: `${sessionId}-${res.turn_index}`,
        user_message: textToSubmit,
        assistant_message: res.answer_detail || res.answer_summary,
        citations: res.citations || [],
        latency_ms: elapsed,
        timestamp: new Date().toISOString()
      };

      setMessages((prev) =>
        prev.map((msg) => (msg.turn_id === tempTurnId ? completedTurn : msg))
      );

      if (res.citations && res.citations.length > 0) {
        setActiveCitations(res.citations);
      }
    } catch (err: any) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      setError(err);
      setMessages((prev) => prev.filter((msg) => msg.turn_id !== tempTurnId));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleOpenCitations = (citationsList: Citation[], index?: number) => {
    setActiveCitations(citationsList);
    setSelectedCitationIdx(index !== undefined ? index : null);
    setIsEvidenceOpen(true);
  };

  if (!sessionId) {
    return (
      <div className="workspace-empty-state">
        <div className="empty-content">
          <span className="empty-icon">⚖️</span>
          <h2>Select or Create a Legal Research Session</h2>
          <p>Choose a multi-turn conversation from the sidebar rail to begin querying statutory provisions.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-container">
      <div className="workspace-main">
        {/* Header */}
        <div className="workspace-header">
          <div className="session-info">
            <h2 className="session-title-text">{sessionTitle || 'Statutory Workspace Session'}</h2>
            <span className="session-id-tag">ID: {sessionId.substring(0, 8)}...</span>
          </div>

          <div className="workspace-header-actions">
            {activeCitations.length > 0 && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setIsEvidenceOpen(!isEvidenceOpen)}
              >
                📜 Evidence Drawer ({activeCitations.length})
              </button>
            )}
          </div>
        </div>

        {/* Messages or Starters */}
        <div className="workspace-messages-area">
          {messages.length === 0 ? (
            <div className="starter-prompts-container">
              <div className="starter-header">
                <h3>Select a Statutory Query Starter</h3>
                <p>Or type your custom legal research question below to execute hybrid vector retrieval.</p>
              </div>

              <div className="starter-grid">
                {STARTER_PROMPTS.map((starter, idx) => (
                  <div
                    key={idx}
                    className="starter-card"
                    onClick={() => handleSubmit(starter.query)}
                  >
                    <h4>{starter.title}</h4>
                    <p>{starter.query}</p>
                    <span className="starter-action">Query Provision →</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-stream">
              {messages.map((turn) => (
                <React.Fragment key={turn.turn_id}>
                  <ChatMessage
                    role="user"
                    content={turn.user_message}
                    timestamp={turn.timestamp}
                  />

                  {turn.assistant_message && (
                    <ChatMessage
                      role="assistant"
                      content={turn.assistant_message}
                      citations={turn.citations}
                      latencyMs={turn.latency_ms}
                      timestamp={turn.timestamp}
                      onOpenEvidence={(idx) => handleOpenCitations(turn.citations || [], idx)}
                    />
                  )}
                </React.Fragment>
              ))}

              {isProcessing && <AgentStepStatus currentStep={currentStep} />}

              <ErrorStateBanner
                error={error}
                onRetry={() => handleSubmit()}
                onDismiss={() => setError(null)}
              />

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="workspace-input-area">
          <form className="input-form" onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
            <textarea
              className="prompt-textarea"
              placeholder="Query statutory provisions (e.g., 'What is the penalty under BNS §103 for murder?')..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
              rows={2}
            />
            <button
              type="submit"
              className="btn btn-primary submit-btn"
              disabled={!prompt.trim() || isProcessing}
            >
              {isProcessing ? 'Analyzing...' : 'Execute Query ⚖️'}
            </button>
          </form>
          <div className="input-disclaimer">
            Press <strong>Enter</strong> to submit query • <strong>Shift+Enter</strong> for line break
          </div>
        </div>
      </div>

      <EvidencePanel
        isOpen={isEvidenceOpen}
        onClose={() => setIsEvidenceOpen(false)}
        citations={activeCitations}
        selectedCitationIndex={selectedCitationIdx}
      />
    </div>
  );
};

export default ChatWorkspace;
