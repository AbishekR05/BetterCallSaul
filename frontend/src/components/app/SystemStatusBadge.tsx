import React, { useEffect, useState } from 'react';
import { healthApi, ReadyResponse } from '../../api/healthApi';
import './SystemStatusBadge.css';

export const SystemStatusBadge: React.FC = () => {
  const [readiness, setReadiness] = useState<ReadyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    const checkStatus = async () => {
      try {
        const data = await healthApi.getReady();
        if (isMounted) {
          setReadiness(data);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setReadiness({
            status: 'not_ready',
            checks: {
              session_db: 'fail',
              corpus_db: 'fail',
              orchestrator: 'fail',
              secrets: 'fail'
            }
          });
          setLoading(false);
        }
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="status-badge checking">
        <span className="dot pulse"></span>
        <span className="status-text">Checking System...</span>
      </div>
    );
  }

  const isHealthy = readiness?.status === 'ready';

  return (
    <div className={`status-badge ${isHealthy ? 'healthy' : 'degraded'}`} title={`DB: ${readiness?.checks?.session_db || 'unknown'} | Corpus: ${readiness?.checks?.corpus_db || 'unknown'}`}>
      <span className={`dot ${isHealthy ? 'green' : 'amber'}`}></span>
      <span className="status-text">
        {isHealthy ? 'Engine Ready' : 'System Degraded'}
      </span>
    </div>
  );
};

export default SystemStatusBadge;
