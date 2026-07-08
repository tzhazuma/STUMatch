import { useCallback, useEffect, useState } from 'react';

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  execute: () => Promise<T | null>;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
  autoExecute = true
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
      return result;
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetcher, ...deps]);

  useEffect(() => {
    if (autoExecute) {
      execute();
    }
  }, [execute, autoExecute]);

  return { data, loading, error, execute };
}
