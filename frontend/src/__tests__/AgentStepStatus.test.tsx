import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AgentStepStatus } from '../components/app/AgentStepStatus';

describe('AgentStepStatus Component', () => {
  it('renders all reasoning steps with current step active', () => {
    render(<AgentStepStatus currentStep="searching" />);

    expect(screen.getByText('Reasoning Pipeline Active')).toBeInTheDocument();
    expect(screen.getByText('Understanding Legal Intent')).toBeInTheDocument();
    expect(screen.getByText('Searching Statutory Corpus')).toBeInTheDocument();
    expect(screen.getByText('Checking Statutory Evidence')).toBeInTheDocument();
    expect(screen.getByText('Synthesizing Grounded Answer')).toBeInTheDocument();
  });

  it('displays step details for active step', () => {
    render(<AgentStepStatus currentStep="checking_evidence" />);

    expect(
      screen.getByText('Applying cross-encoder re-ranking & validating statutory provisions')
    ).toBeInTheDocument();
  });
});
