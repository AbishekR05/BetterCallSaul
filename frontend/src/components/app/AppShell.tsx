import React, { useState } from 'react';
import { SessionSidebar } from './SessionSidebar';
import { ChatWorkspace } from './ChatWorkspace';
import { SystemStatusBadge } from './SystemStatusBadge';
import './AppShell.css';

export const AppShell: React.FC = () => {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionTitle, setActiveSessionTitle] = useState<string>('');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  const handleSelectSession = (id: string, title: string) => {
    setActiveSessionId(id);
    setActiveSessionTitle(title);
  };

  const handleNewSessionCreated = (id: string, title: string) => {
    setActiveSessionId(id);
    setActiveSessionTitle(title);
  };

  return (
    <div className="app-shell-layout">
      {/* Sidebar Rail */}
      <div className={`sidebar-wrapper ${isSidebarOpen ? 'open' : 'closed'}`}>
        <SessionSidebar
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSessionCreated={handleNewSessionCreated}
        />
      </div>

      {/* Main Content Area */}
      <div className="workspace-wrapper">
        {/* Top Control Bar */}
        <header className="workspace-top-bar">
          <div className="bar-left">
            <button
              className="toggle-sidebar-btn"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title="Toggle History Sidebar"
            >
              ☰
            </button>
            <span className="workspace-brand-label">Legal Reasoning Workspace</span>
          </div>

          <div className="bar-right">
            <SystemStatusBadge />
          </div>
        </header>

        {/* Workspace Body */}
        <main className="workspace-body">
          <ChatWorkspace
            sessionId={activeSessionId}
            sessionTitle={activeSessionTitle}
          />
        </main>
      </div>
    </div>
  );
};
