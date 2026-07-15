import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, access_token } = useAuthStore();
  const ok = isAuthenticated && !!access_token;
  return ok ? <>{children}</> : <Navigate to="/login" replace />;
}
