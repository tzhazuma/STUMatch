import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Bell } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { UserCard } from '@/components/UserCard';
import { Modal } from '@/components/ui/Modal';
import {
  discoveryUsers,
  setPush,
  sendFriendRequest,
  getMyProfile,
} from '@/api/endpoints';
import type { DiscoveryItem, Profile, Section } from '@/types';

const sections: { key: Section; label: string }[] = [
  { key: 'academic', label: '学术交流' },
  { key: 'daily', label: '日常生活' },
  { key: 'dating', label: '恋爱交友' },
];

export default function Discovery() {
  const { section = 'academic' } = useParams<{ section: Section }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [users, setUsers] = useState<DiscoveryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState(searchParams.get('q') || '');
  const [push, setPushEnabled] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [modal, setModal] = useState<{ open: boolean; title: string; message: string }>({
    open: false,
    title: '',
    message: '',
  });

  useEffect(() => {
    getMyProfile().then(setProfile).catch(() => {});
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [section, q, push]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await discoveryUsers(section as Section, {
        q: q || undefined,
        push,
        page: 1,
        limit: 20,
      });
      setUsers(data.items || []);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(q ? { q } : {});
    fetchUsers();
  };

  const handleTogglePush = async () => {
    if (!profile?.is_verified_email) {
      setModal({
        open: true,
        title: '完善交友资料，开启精确匹配',
        message: '请先完成邮箱验证，并完善个人资料后，再开启推送。',
      });
      return;
    }
    const enabled = !push;
    await setPush(section as Section, { enabled });
    setPushEnabled(enabled);
  };

  const handleAddFriend = async (user: DiscoveryItem) => {
    if (!profile?.is_verified_email) {
      setModal({
        open: true,
        title: '完善交友资料，开启精确匹配',
        message: '请先完成邮箱验证，并完善个人资料后，再加好友。',
      });
      return;
    }
    try {
      await sendFriendRequest({ to_user_id: user.user_id, message: '想认识你' });
      alert('好友申请已发送');
    } catch (e: any) {
      alert(e?.response?.data?.message || '发送失败');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 rounded-xl bg-white p-1 shadow-sm">
        {sections.map((s) => (
          <a
            key={s.key}
            href={`/discovery/${s.key}`}
            onClick={(e) => {
              e.preventDefault();
              navigate(`/discovery/${s.key}`);
            }}
            className={`flex-1 rounded-lg py-2 text-center text-sm font-medium transition ${
              section === s.key ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {s.label}
          </a>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜索昵称、专业、学校..."
              className="pl-9"
            />
          </div>
        </form>
        <Button variant={push ? 'primary' : 'secondary'} onClick={handleTogglePush} className="flex items-center gap-1">
          <Bell className="h-4 w-4" />
          {push ? '已开启' : '开启推送'}
        </Button>
      </div>

      {loading ? (
        <p className="text-center text-sm text-gray-500">加载中...</p>
      ) : users.length === 0 ? (
        <Card className="py-12 text-center text-sm text-gray-500">暂无用户</Card>
      ) : (
        <div className="space-y-3">
          {users.map((u) => (
            <UserCard key={u.user_id} user={u} section={section as Section} onAddFriend={handleAddFriend} />
          ))}
        </div>
      )}

      <Modal
        isOpen={modal.open}
        onClose={() => setModal({ ...modal, open: false })}
        title={modal.title}
        footer={
          <Button onClick={() => setModal({ ...modal, open: false })} variant="secondary">
            知道了
          </Button>
        }
      >
        {modal.message}
      </Modal>
    </div>
  );
}
