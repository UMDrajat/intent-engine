import { useState, useEffect, useRef } from 'react';
import { mockLiveMetrics } from '../api/mockData';

export function useWebSocket(url) {
  const [metrics, setMetrics] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  const maxRetries = 3;

  useEffect(() => {
    let unmounted = false;

    function connect() {
      if (unmounted) return;
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          if (unmounted) return;
          setConnected(true);
          retriesRef.current = 0;
        };

        ws.onmessage = (event) => {
          if (unmounted) return;
          try {
            setMetrics(JSON.parse(event.data));
          } catch { /* ignore parse errors */ }
        };

        ws.onclose = () => {
          if (unmounted) return;
          setConnected(false);
          if (retriesRef.current < maxRetries) {
            retriesRef.current += 1;
            const delay = Math.min(1000 * 2 ** retriesRef.current, 8000);
            setTimeout(connect, delay);
          } else {
            // Fall back to mock data
            setMetrics(mockLiveMetrics);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        // WebSocket constructor failed, use mock
        setMetrics(mockLiveMetrics);
      }
    }

    connect();

    return () => {
      unmounted = true;
      if (wsRef.current) wsRef.current.close();
    };
  }, [url]);

  return { metrics, connected };
}
