import { useCallback, useEffect, useState } from 'react';
import { fetchMonthlyAnalytics } from '../services/api.js';

export function useMonthlyAnalytics(year, month) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setError('');
    setData(null);

    fetchMonthlyAnalytics(year, month, controller.signal)
      .then((result) => {
        if (!current) return;
        setData(result);
        setLoading(false);
      })
      .catch((requestError) => {
        if (!current || requestError.name === 'AbortError') return;
        setError(requestError.message || 'Something went wrong while loading this report.');
        setLoading(false);
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [year, month, attempt]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { data, loading, error, retry };
}
