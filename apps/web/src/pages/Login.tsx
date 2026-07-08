import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';
import { sendVerificationCode } from '@/api/endpoints';

export default function Login() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('上海科技大学');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [codeSent, setCodeSent] = useState(false);

  const handleSendCode = async () => {
    if (!email) return;
    setLoading(true);
    try {
      await sendVerificationCode({ email, phone: null, purpose: mode === 'register' ? 'register' : 'login' });
      setCodeSent(true);
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || '发送失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register({ email, code, password, nickname, school });
      }
      navigate('/discovery/academic');
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <h1 className="mb-2 text-center text-2xl font-bold text-brand-600">UniMatch</h1>
        <p className="mb-6 text-center text-sm text-gray-500">校园同行匹配</p>

        <div className="mb-4 flex rounded-lg bg-gray-100 p-1">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              mode === 'login' ? 'bg-white text-brand-600 shadow' : 'text-gray-500'
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              mode === 'register' ? 'bg-white text-brand-600 shadow' : 'text-gray-500'
            }`}
          >
            注册
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="邮箱"
            type="email"
            placeholder="yourname@shanghaitech.edu.cn"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {mode === 'register' && (
            <>
              <div className="flex gap-2">
                <Input
                  label="验证码"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
                <Button type="button" variant="secondary" onClick={handleSendCode} isLoading={loading} className="mt-6">
                  {codeSent ? '已发送' : '发送验证码'}
                </Button>
              </div>
              <Input label="昵称" value={nickname} onChange={(e) => setNickname(e.target.value)} required />
              <Input label="学校" value={school} onChange={(e) => setSchool(e.target.value)} required />
            </>
          )}
          <Input
            label="密码"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" isLoading={loading} className="w-full">
            {mode === 'login' ? '登录' : '注册'}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          注册即表示同意服务协议与隐私政策
        </p>
      </Card>
    </div>
  );
}
