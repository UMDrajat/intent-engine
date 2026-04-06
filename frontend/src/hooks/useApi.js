import { useState, useEffect, useCallback } from 'react';

export function useApi(apiFn, mockData, { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const [isDemo, setIsDemo] = useState(false);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn(...args);
      setData(result);
      setIsDemo(false);
    } catch (err) {
      console.warn('API unavailable, using demo data:', err.message);
      setData(typeof mockData === 'function' ? mockData(...args) : mockData);
      setIsDemo(true);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [apiFn, mockData]);

  useEffect(() => {
    if (immediate) execute();
  }, [immediate, execute]);

  return { data, loading, error, isDemo, refetch: execute };
}
