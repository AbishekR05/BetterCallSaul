import React from 'react';
import DOMPurify from 'dompurify';
import { Citation } from '../../api/turnsApi';
import './ChatMessage.css';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  latencyMs?: number;
  timestamp?: string;
  onOpenEvidence?: (citationIndex?: number) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  citations = [],
  latencyMs,
  timestamp,
  onOpenEvidence
}) => {
  const isUser = role === 'user';

  const getSanitizedContent = () => {
    if (isUser) return content;

    let formatted = content.replace(/\[(BNS|BNSS|BSS|IPC|CrPC|IEA)\s*(?:§|Sec|Section)?\s*(\d+[^\]]*)\]/gi, (match) => {
      return `<span class="inline-citation-badge" data-citation="${match}">${match}</span>`;
    });

    formatted = formatted
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br/>');

    return DOMPurify.sanitize(formatted, {
      ADD_ATTR: ['data-citation', 'class']
    });
  };

  const handleContainerClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('inline-citation-badge')) {
      if (onOpenEvidence) {
        onOpenEvidence();
      }
    }
  };

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      <div className="message-avatar">
        {isUser ? (
          <span className="user-initial font-serif">A</span>
        ) : (
          <svg className="assistant-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 3v18M4 7h16M4 7l4 8M12 7l-4 8M12 7l4 8M20 7l-4 8M2 15h8M14 15h8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </div>

      <div className="message-bubble-wrapper">
        <div className="message-meta-header">
          <span className="sender-name">{isUser ? 'Legal Advocate' : 'BetterCallSaul Intelligence'}</span>
          {timestamp && <span className="timestamp">{new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
        </div>

        <div className="message-bubble">
          {isUser ? (
            <p className="user-text">{content}</p>
          ) : (
            <div
              className="assistant-text markdown-content"
              dangerouslySetInnerHTML={{ __html: getSanitizedContent() }}
              onClick={handleContainerClick}
            />
          )}
        </div>

        {!isUser && (
          <div className="message-footer-meta">
            {citations.length > 0 && (
              <button
                className="evidence-trigger-btn"
                onClick={() => onOpenEvidence && onOpenEvidence()}
              >
                {citations.length} Statutory Citation{citations.length > 1 ? 's' : ''} Retrieved <span>→</span>
              </button>
            )}

            {latencyMs !== undefined && (
              <span className="latency-tag">
                {(latencyMs / 1000).toFixed(2)}s latency
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
