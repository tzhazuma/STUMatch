import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';
import { sendVerificationCode } from '@/api/endpoints';
import { Sparkles, ShieldCheck, Mail, Lock, User, School, Ticket } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('上海科技大学');
  const [referralCode, setReferralCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [agreed, setAgreed] = useState(false);

  const handleSendCode = async () => {
    if (!email || countdown > 0) return;
    setLoading(true);
    try {
      await sendVerificationCode({ email, purpose: mode === 'register' ? 'register' : 'login' });
      setCodeSent(true);
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) { clearInterval(timer); return 0; }
          return prev - 1;
        });
      }, 1000);
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || '发送失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (mode === 'register' && !agreed) {
      setError('请先阅读并同意服务协议和隐私政策');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register({ email, code, password, nickname, school, referral_code: referralCode || undefined });
      }
      navigate('/discovery/academic');
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-slate-50 via-brand-50 to-accent-50" />
      <div className="absolute -left-20 -top-20 h-72 w-72 rounded-full bg-brand-200/40 blur-3xl" />
      <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-accent-200/30 blur-3xl" />

      <div className="w-full max-w-md animate-slide-up">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gradient">SKDMatch</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">科爱捏 · 校内互助交流平台</p>
        </div>

        <Card className="glass p-6 shadow-elevated">
          <div className="mb-6 flex rounded-2xl bg-slate-100 p-1.5">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`flex-1 rounded-xl py-2.5 text-sm font-bold transition-all ${
                mode === 'login'
                  ? 'bg-white text-brand-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              登录
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`flex-1 rounded-xl py-2.5 text-sm font-bold transition-all ${
                mode === 'register'
                  ? 'bg-white text-brand-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              注册
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3.5 top-9 h-4 w-4 text-slate-400" />
              <Input
                label="邮箱"
                type="email"
                placeholder="yourname@shanghaitech.edu.cn"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10"
                required
              />
            </div>

            {mode === 'register' && (
              <>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      label="验证码"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="6位验证码"
                      required
                    />
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleSendCode}
                    isLoading={loading}
                    className="mt-7 shrink-0"
                  >
                    {countdown > 0 ? `${countdown}s` : codeSent ? '重新发送' : '发送验证码'}
                  </Button>
                </div>
                <div className="relative">
                  <User className="absolute left-3.5 top-9 h-4 w-4 text-slate-400" />
                  <Input label="昵称" value={nickname} onChange={(e) => setNickname(e.target.value)} className="pl-10" required />
                </div>
                <div className="relative">
                  <School className="absolute left-3.5 top-9 h-4 w-4 text-slate-400" />
                  <Input label="学校" value={school} onChange={(e) => setSchool(e.target.value)} className="pl-10" required />
                </div>
                <div className="relative">
                  <Ticket className="absolute left-3.5 top-9 h-4 w-4 text-slate-400" />
                  <Input
                    label="邀请码（选填）"
                    placeholder="如有好友邀请码可填写"
                    value={referralCode}
                    onChange={(e) => setReferralCode(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <label className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={agreed}
                    onChange={(e) => setAgreed(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span>
                    我已阅读并同意
                    <Link to="/legal/terms" className="font-semibold text-brand-600 hover:underline">《用户服务协议》</Link>
                    和
                    <Link to="/legal/privacy" className="font-semibold text-brand-600 hover:underline">《隐私保护协议》</Link>
                  </span>
                </label>
              </>
            )}

            <div className="relative">
              <Lock className="absolute left-3.5 top-9 h-4 w-4 text-slate-400" />
              <Input
                label="密码"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-10"
                required
              />
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 px-4 py-3 text-xs font-medium text-red-600">
                {error}
              </div>
            )}

            <Button type="submit" isLoading={loading} className="w-full shadow-soft">
              {mode === 'login' ? '立即登录' : '创建账号'}
            </Button>
          </form>

          <div className="mt-5 flex items-center justify-center gap-1.5 text-xs text-slate-500">
            <ShieldCheck className="h-3.5 w-3.5 text-brand-500" />
            <span>注册即表示同意服务协议与隐私政策</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
