import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Users, UserCircle, MessageCircle, LogOut, Sparkles } from 'lucide-react';
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
    <div className="flex min-h-full flex-col bg-slate-50">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-2xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-soft">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-extrabold text-gradient">SKDMatch</span>
          </Link>
          <div className="flex items-center gap-2">
            {user && (
              <button
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                title="退出"
              >
                <LogOut className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-36 pt-5">
        <Outlet />
      </main>

      <nav className="fixed bottom-4 left-1/2 z-40 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-2xl border border-slate-100 bg-white/90 px-2 pb-safe pt-2 shadow-elevated backdrop-blur-xl">
        <div className="flex justify-around">
          {nav.map((item) => {
            const active = isActive(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex flex-1 flex-col items-center gap-1 rounded-xl py-2.5 text-xs font-bold transition-all ${
                  active ? 'text-brand-600' : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                <Icon className={`h-6 w-6 transition ${active ? 'fill-current' : ''}`} />
                {item.label}
                {active && (
                  <span className="absolute -top-1 h-1 w-6 rounded-full bg-gradient-to-r from-brand-500 to-accent-500" />
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
