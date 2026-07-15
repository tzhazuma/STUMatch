import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getLegalDoc } from '@/api/endpoints';

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
    return <div className="p-8 text-center text-gray-500">加载中…</div>;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-500">{error || '文档不存在'}</p>
        <Link to="/login" className="mt-4 inline-block text-brand-600 hover:underline">
          返回登录
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-600">{data.title}</h1>
        <Link to="/login" className="text-sm text-brand-600 hover:underline">
          返回登录
        </Link>
      </div>
      <p className="mb-4 text-xs text-gray-400">
        最后更新：{new Date(data.updated_at).toLocaleDateString('zh-CN')}
      </p>
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-gray-700">
          {data.content}
        </pre>
      </div>
    </div>
  );
}
