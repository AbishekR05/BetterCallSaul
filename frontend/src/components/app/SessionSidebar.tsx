import React, { useState, useEffect } from 'react';
import { sessionsApi, SessionItem } from '../../api/sessionsApi';
import { useAuth } from '../../context/AuthContext';
import './SessionSidebar.css';

interface SessionSidebarProps {
  activeSessionId: string | null;
  onSelectSession: (id: string, title: string) => void;
  onNewSessionCreated: (id: string, title: string) => void;
}

export const SessionSidebar: React.FC<SessionSidebarProps> = ({
  activeSessionId,
  onSelectSession,
  onNewSessionCreated
}) => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>('');

  const loadSessions = async () => {
    setIsLoading(true);
    try {
      const res = await sessionsApi.listSessions();
      const mapped = (res.sessions || []).map((s, idx) => ({
        id: s.session_id,
        title: `Legal Session ${idx + 1} (${s.session_id.substring(0, 6)})`
      }));
      setSessions(mapped);
      if (mapped.length > 0 && !activeSessionId) {
        onSelectSession(mapped[0].id, mapped[0].title);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleCreateNew = async () => {
    try {
      const newSess: SessionItem = await sessionsApi.createSession();
      const title = `Legal Session ${sessions.length + 1} (${newSess.session_id.substring(0, 6)})`;
      const newItem = { id: newSess.session_id, title };
      setSessions([newItem, ...sessions]);
      onNewSessionCreated(newItem.id, newItem.title);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleStartEdit = (e: React.MouseEvent, sess: { id: string; title: string }) => {
    e.stopPropagation();
    setEditingId(sess.id);
    setEditingTitle(sess.title);
  };

  const handleSaveRename = (e: React.FormEvent, id: string) => {
    e.preventDefault();
    if (!editingTitle.trim()) return;

    setSessions(sessions.map((s) => (s.id === id ? { ...s, title: editingTitle.trim() } : s)));
    setEditingId(null);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this legal research session?')) return;

    try {
      await sessionsApi.deleteSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id && remaining.length > 0) {
        onSelectSession(remaining[0].id, remaining[0].title);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  return (
    <aside className="session-sidebar">
      {/* Brand & New Session */}
      <div className="sidebar-header">
        <div className="sidebar-brand font-serif">
          <svg className="sidebar-scale-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <path d="M12 3v18M4 7h16M4 7l4 8M12 7l-4 8M12 7l4 8M20 7l-4 8M2 15h8M14 15h8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="brand-name font-serif">BetterCallSaul</span>
        </div>
        <button className="btn btn-primary new-session-btn" onClick={handleCreateNew}>
          + New Research Session
        </button>
      </div>

      {/* Sessions List */}
      <div className="sidebar-sessions-list">
        <div className="sessions-list-header">
          <span>Active Workspace History</span>
          <span className="count-tag">{sessions.length}</span>
        </div>

        {isLoading ? (
          <div className="sidebar-loading">Loading history...</div>
        ) : sessions.length === 0 ? (
          <div className="sidebar-empty">No active sessions. Click "+ New Research Session" above.</div>
        ) : (
          sessions.map((sess) => {
            const isActive = sess.id === activeSessionId;
            const isEditing = sess.id === editingId;

            return (
              <div
                key={sess.id}
                className={`session-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectSession(sess.id, sess.title)}
              >
                {isEditing ? (
                  <form
                    onSubmit={(e) => handleSaveRename(e, sess.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="rename-form"
                  >
                    <input
                      type="text"
                      className="rename-input"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      autoFocus
                      onBlur={(e) => handleSaveRename(e, sess.id)}
                    />
                  </form>
                ) : (
                  <span className="session-item-title">{sess.title}</span>
                )}

                <div className="session-item-actions">
                  {!isEditing && (
                    <>
                      <button
                        className="item-action-btn"
                        title="Rename"
                        onClick={(e) => handleStartEdit(e, sess)}
                      >
                        Rename
                      </button>
                      <button
                        className="item-action-btn"
                        title="Delete"
                        onClick={(e) => handleDelete(e, sess.id)}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* User Info & Logout */}
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="avatar-circle font-serif">
            {user?.username ? user.username[0].toUpperCase() : 'A'}
          </div>
          <div className="user-meta">
            <span className="user-name">{user?.username || 'Advocate User'}</span>
            <span className="user-role">Authenticated Counsel</span>
          </div>
        </div>

        <button className="logout-btn" onClick={() => logout()} title="Sign Out">
          Logout
        </button>
      </div>
    </aside>
  );
};

export default SessionSidebar;
