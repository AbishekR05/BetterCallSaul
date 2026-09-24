import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ChatMessage } from '../components/app/ChatMessage';

describe('ChatMessage Component', () => {
  it('renders user message cleanly', () => {
    render(<ChatMessage role="user" content="What is BNS Section 103?" />);
    expect(screen.getByText('What is BNS Section 103?')).toBeInTheDocument();
    expect(screen.getByText('Legal Advocate')).toBeInTheDocument();
  });

  it('sanitizes malicious script tags via DOMPurify in assistant answers', () => {
    const maliciousInput = 'Legal response <script>alert("xss")</script> **safe text**';
    render(<ChatMessage role="assistant" content={maliciousInput} />);

    expect(screen.getByText('BetterCallSaul Intelligence')).toBeInTheDocument();
    expect(screen.queryByText('alert("xss")')).not.toBeInTheDocument();
    expect(screen.getByText('safe text')).toBeInTheDocument();
  });

  it('parses statutory citations into inline clickable badges', () => {
    const citationInput = 'Under [BNS §103], murder is punishable by death or life imprisonment.';
    const { container } = render(<ChatMessage role="assistant" content={citationInput} />);

    const badge = container.querySelector('.inline-citation-badge');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toBe('[BNS §103]');
  });
});
