import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MapPin, GraduationCap, Heart, MessageCircle, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { discoveryUserDetail, sendFriendRequest } from '@/api/endpoints';
import type { DiscoveryDetail, Section } from '@/types';

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

  if (loading) return <p className="text-center text-sm text-gray-500">加载中...</p>;
  if (!user) return <p className="text-center text-sm text-gray-500">用户不存在</p>;

  return (
    <div className="space-y-4">
      <Card className="flex items-center gap-4">
        {user.avatar_url ? (
          <img src={user.avatar_url} alt="avatar" className="h-20 w-20 rounded-full object-cover" />
        ) : (
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-100 text-2xl font-bold text-brand-600">
            {user.nickname?.[0] || '?'}
          </div>
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">{user.nickname}</h1>
            {typeof user.match_score === 'number' && (
              <Badge variant="info" className="flex items-center gap-1">
                <Heart className="h-3 w-3" />
                {Math.round(user.match_score * 100)}%
              </Badge>
            )}
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-sm text-gray-500">
            {user.age && <span>{user.age} 岁</span>}
            {user.education_level && (
              <span className="flex items-center gap-1">
                <GraduationCap className="h-4 w-4" />
                {user.education_level}
              </span>
            )}
            {user.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {user.location}
              </span>
            )}
          </div>
          {user.match_reason && <p className="mt-2 text-sm text-brand-600">{user.match_reason}</p>}
        </div>
      </Card>

      <Card className="space-y-3">
        {section === 'academic' && (
          <>
            <p className="text-sm"><span className="font-medium">专业：</span>{user.major || '未填写'}</p>
            <p className="text-sm"><span className="font-medium">学术方向：</span>{user.research_direction || '未填写'}</p>
          </>
        )}
        {section === 'daily' && (
          <>
            <p className="text-sm"><span className="font-medium">MBTI：</span>{user.mbti || '未填写'}</p>
            <p className="text-sm"><span className="font-medium">个人介绍：</span>{user.bio || '未填写'}</p>
          </>
        )}
        {section === 'dating' && (
          <>
            <p className="text-sm"><span className="font-medium">交友目的：</span>{user.dating_purpose || '未填写'}</p>
            <p className="text-sm"><span className="font-medium">想遇见的人：</span>{user.ideal_person || '未填写'}</p>
            <p className="text-sm"><span className="font-medium">家庭状况：</span>{user.family_status || '未填写'}</p>
          </>
        )}
        {user.interests && user.interests.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {user.interests.map((tag) => (
              <span key={tag} className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
                {tag}
              </span>
            ))}
          </div>
        )}
      </Card>

      <div className="flex gap-3">
        <Button onClick={handleAddFriend} className="flex-1 flex items-center justify-center gap-2">
          <UserPlus className="h-4 w-4" />
          加好友
        </Button>
        <Button variant="secondary" onClick={() => navigate('/chat/new')} className="flex-1 flex items-center justify-center gap-2">
          <MessageCircle className="h-4 w-4" />
          聊天
        </Button>
      </div>
    </div>
  );
}
