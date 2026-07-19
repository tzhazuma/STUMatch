import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MapPin, GraduationCap, Heart, MessageCircle, UserPlus, Star, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { discoveryUserDetail, sendFriendRequest } from '@/api/endpoints';
import type { DiscoveryDetail, Section } from '@/types';

const tagColors = [
  'bg-brand-50 text-brand-700',
  'bg-sky-50 text-sky-700',
  'bg-emerald-50 text-emerald-700',
  'bg-amber-50 text-amber-700',
  'bg-rose-50 text-rose-700',
  'bg-violet-50 text-violet-700',
];

export default function UserDetail() {
  const { section = 'academic', userId } = useParams<{ section: Section; userId: string }>();
  const navigate = useNavigate();
  const [user, setUser] = useState<DiscoveryDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    discoveryUserDetail(section as Section, userId)
      .then(setUser)
      .finally(() => setLoading(false));
  }, [section, userId]);

  const handleAddFriend = async () => {
    if (!userId) return;
    try {
      await sendFriendRequest({ to_user_id: userId, message: '想认识你' });
      alert('好友申请已发送');
    } catch (e: any) {
      alert(e?.response?.data?.message || '发送失败');
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
      <p className="text-sm">加载中...</p>
    </div>
  );
  if (!user) return <p className="py-20 text-center text-sm text-slate-400">用户不存在</p>;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-500 to-accent-500 p-6 text-white shadow-elevated">
        <Sparkles className="absolute -right-4 -top-4 h-32 w-32 text-white/10" />
        <div className="relative z-10 flex items-center gap-5">
          <Avatar src={user.avatar_url} alt={user.nickname} size="xl" fallback={user.nickname?.[0] || '?'} ring />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold">{user.nickname}</h1>
              {typeof user.match_score === 'number' && (
                <Badge className="bg-white/20 text-white border-0">
                  <Star className="mr-1 h-3 w-3 fill-current" />
                  {Math.round(user.match_score * 100)}%
                </Badge>
              )}
            </div>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-white/90">
              {user.age && <span>{user.age} 岁</span>}
              {user.education_level && (
                <span className="flex items-center gap-1">
                  <GraduationCap className="h-3.5 w-3.5" />
                  {user.education_level}
                </span>
              )}
              {user.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {user.location}
                </span>
              )}
            </div>
            {user.match_reason && (
              <p className="mt-3 inline-flex items-center gap-1 rounded-xl bg-white/20 px-3 py-1 text-xs backdrop-blur">
                <Heart className="h-3 w-3" />
                {user.match_reason}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Details */}
      <Card className="space-y-4">
        {section === 'academic' && (
          <>
            <DetailRow label="专业" value={user.major} />
            <DetailRow label="学术方向" value={user.research_direction} />
          </>
        )}
        {section === 'daily' && (
          <>
            <DetailRow label="MBTI" value={user.mbti} />
            <DetailRow label="个人介绍" value={user.bio} />
          </>
        )}
        {section === 'dating' && (
          <>
            <DetailRow label="交友目的" value={user.dating_purpose} />
            <DetailRow label="想遇见的人" value={user.ideal_person} />
            <DetailRow label="家庭状况" value={user.family_status} />
          </>
        )}
        {user.interests && user.interests.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {user.interests.map((tag, idx) => (
              <span
                key={tag}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${tagColors[idx % tagColors.length]}`}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Button onClick={handleAddFriend} className="flex items-center justify-center gap-2">
          <UserPlus className="h-4 w-4" />
          加好友
        </Button>
        <Button variant="secondary" onClick={() => navigate('/chat/new')} className="flex items-center justify-center gap-2">
          <MessageCircle className="h-4 w-4" />
          聊天
        </Button>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="text-sm">
      <span className="font-bold text-slate-900">{label}：</span>
      <span className="text-slate-600">{value || '未填写'}</span>
    </div>
  );
}
