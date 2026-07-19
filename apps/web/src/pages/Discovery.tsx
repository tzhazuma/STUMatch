import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Bell, Sparkles, BookOpen, Coffee, Heart, Users } from 'lucide-react';
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

const sections: { key: Section; label: string; icon: React.ElementType; slogan: string }[] = [
  { key: 'academic', label: '学术交流', icon: BookOpen, slogan: '找到志同道合的学术伙伴' },
  { key: 'daily', label: '日常生活', icon: Coffee, slogan: '遇见有趣的校园生活搭子' },
  { key: 'dating', label: '恋爱交友', icon: Heart, slogan: '在校园里遇见心动的 TA' },
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

  const currentSection = sections.find((s) => s.key === section) || sections[0];
  const SectionIcon = currentSection.icon;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-500 to-accent-500 p-6 text-white shadow-elevated">
        <div className="relative z-10">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
            <SectionIcon className="h-5 w-5 text-white" />
          </div>
          <h2 className="text-2xl font-extrabold">{currentSection.label}</h2>
          <p className="mt-1 text-sm text-white/90">{currentSection.slogan}</p>
        </div>
        <Sparkles className="absolute -bottom-4 -right-4 h-32 w-32 text-white/10" />
        <Users className="absolute -right-2 top-4 h-24 w-24 text-white/10" />
      </div>

      {/* Section tabs */}
      <div className="flex gap-2 rounded-2xl bg-white p-1.5 shadow-card">
        {sections.map((s) => {
          const Icon = s.icon;
          return (
            <a
              key={s.key}
              href={`/discovery/${s.key}`}
              onClick={(e) => {
                e.preventDefault();
                navigate(`/discovery/${s.key}`);
              }}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs font-bold transition-all ${
                section === s.key
                  ? 'bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-soft'
                  : 'text-slate-500 hover:bg-slate-50'
              }`}
            >
              <Icon className="h-4 w-4" />
              {s.label}
            </a>
          );
        })}
      </div>

      {/* Search & push */}
      <div className="flex items-center gap-3">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜索昵称、专业、学校..."
              className="pl-10"
            />
          </div>
        </form>
        <Button
          variant={push ? 'primary' : 'secondary'}
          onClick={handleTogglePush}
          className="flex shrink-0 items-center gap-1.5 shadow-sm"
        >
          <Bell className={`h-4 w-4 ${push ? 'fill-current' : ''}`} />
          {push ? '已开启' : '开启推送'}
        </Button>
      </div>

      {/* User list */}
      {loading ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
          <p className="text-sm">正在寻找合适的伙伴...</p>
        </div>
      ) : users.length === 0 ? (
        <Card className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
            <Search className="h-7 w-7 text-slate-400" />
          </div>
          <p className="text-base font-semibold text-slate-700">暂无匹配用户</p>
          <p className="mt-1 text-sm text-slate-400">完善资料或切换板块，发现更多同学</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {users.map((u, idx) => (
            <div
              key={u.user_id}
              className="animate-slide-up"
              style={{ animationDelay: `${idx * 60}ms`, animationFillMode: 'both' }}
            >
              <UserCard user={u} section={section as Section} onAddFriend={handleAddFriend} />
            </div>
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
