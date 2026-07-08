import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Users, UserCircle, MessageCircle, LogOut } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export function Layout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();

  const nav = [
    { path: '/discovery/academic', label: '发现', icon: Users },
    { path: '/friends', label: '好友', icon: MessageCircle },
    { path: '/profile', label: '个人', icon: UserCircle },
  ];

  const isActive = (path: string) => pathname.startsWith(path.split('/:')[0]);

  return (
    <div className="flex min-h-full flex-col bg-gray-50">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <Link to="/" className="text-lg font-bold text-brand-600">
            UniMatch
          </Link>
          <div className="flex items-center gap-2">
            {user && (
              <button
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                className="rounded p-2 text-gray-500 hover:bg-gray-100"
                title="退出"
              >
                <LogOut className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-24 pt-4">
        <Outlet />
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white pb-safe pt-2">
        <div className="mx-auto flex max-w-3xl justify-around px-4">
          {nav.map((item) => {
            const active = isActive(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-1 flex-col items-center gap-1 py-2 text-xs font-medium transition ${
                  active ? 'text-brand-600' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className={`h-6 w-6 ${active ? 'fill-current' : ''}`} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
