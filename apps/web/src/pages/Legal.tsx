import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getLegalDoc } from '@/api/endpoints';
import { Card } from '@/components/ui/Card';
import { ArrowLeft, FileText } from 'lucide-react';

interface LegalDoc {
  title: string;
  content: string;
  updated_at: string;
}

export default function Legal() {
  const { doc } = useParams<{ doc: string }>();
  const [data, setData] = useState<LegalDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!doc) return;
    const slug = doc === 'privacy' ? 'privacy' : 'terms';
    setLoading(true);
    setError('');
    getLegalDoc(slug)
      .then(setData)
      .catch((e: any) => {
        setError(e?.response?.data?.message || e?.message || '加载失败');
      })
      .finally(() => setLoading(false));
  }, [doc]);

  if (loading) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-3 text-slate-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
        <p className="text-sm">加载中…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center p-8 text-center">
        <p className="text-red-500">{error || '文档不存在'}</p>
        <Link to="/login" className="mt-4 inline-block text-sm font-bold text-brand-600 hover:underline">
          返回登录
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-full max-w-2xl bg-slate-50 px-4 py-6">
      <Link to="/" className="mb-5 inline-flex items-center gap-1.5 text-sm font-bold text-slate-500 transition hover:text-brand-600">
        <ArrowLeft className="h-4 w-4" />
        返回
      </Link>
      <Card className="overflow-hidden">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-slate-900">{data.title}</h1>
            <p className="text-xs text-slate-400">
              最后更新：{new Date(data.updated_at).toLocaleDateString('zh-CN')}
            </p>
          </div>
        </div>
        <div className="max-h-[70vh] overflow-y-auto rounded-2xl bg-slate-50 p-5">
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-700">
            {data.content}
          </pre>
        </div>
      </Card>
    </div>
  );
}
