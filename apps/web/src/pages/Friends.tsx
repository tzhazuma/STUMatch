import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { listFriends, listFriendRequests, acceptFriendRequest, rejectFriendRequest } from '@/api/endpoints';
import type { Friend, FriendRequest } from '@/types';
import { Users, UserCheck, UserX, MessageCircle, Inbox } from 'lucide-react';

export default function Friends() {
  const navigate = useNavigate();
  const [friends, setFriends] = useState<Friend[]>([]);
  const [requests, setRequests] = useState<FriendRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    setLoading(true);
    const [f, r] = await Promise.all([listFriends(), listFriendRequests('received')]);
    setFriends(f);
    setRequests(r.items);
    setLoading(false);
  };

  useEffect(() => {
    fetch();
  }, []);

  const handleAccept = async (id: string) => {
    await acceptFriendRequest(id);
    fetch();
  };

  const handleReject = async (id: string) => {
    await rejectFriendRequest(id);
    fetch();
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
      <p className="text-sm">加载中...</p>
    </div>
  );

  return (
    <div className="space-y-5 animate-fade-in">
      <h1 className="text-xl font-extrabold text-slate-900">好友</h1>

      {requests.length > 0 && (
        <div className="space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-500">
            <Inbox className="h-4 w-4" />
            好友申请
          </h2>
          {requests.map((req) => (
            <Card key={req.id} className="flex items-center justify-between border-amber-100 bg-gradient-to-r from-amber-50/50 to-white p-4">
              <div className="flex items-center gap-3">
                <Avatar src={req.from_user?.avatar_url} fallback={req.from_user?.nickname?.[0] || '?'} size="md" />
                <div>
                  <p className="font-bold text-slate-900">{req.from_user?.nickname || '用户'}</p>
                  <p className="text-xs text-slate-500">{req.message || '想加你为好友'}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleAccept(req.id)}>
                  <UserCheck className="mr-1 h-3.5 w-3.5" />
                  接受
                </Button>
                <Button size="sm" variant="secondary" onClick={() => handleReject(req.id)}>
                  <UserX className="mr-1 h-3.5 w-3.5" />
                  拒绝
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="space-y-3">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-500">
          <Users className="h-4 w-4" />
          我的好友
        </h2>
        {friends.length === 0 ? (
          <Card className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
              <MessageCircle className="h-7 w-7 text-slate-400" />
            </div>
            <p className="text-base font-semibold text-slate-700">还没有好友</p>
            <p className="mt-1 text-sm text-slate-400">去“发现”页找到志同道合的同学吧</p>
          </Card>
        ) : (
          <div className="grid gap-3">
            {friends.map((f) => (
              <Card
                key={f.user_id}
                hover
                className="flex cursor-pointer items-center gap-4 p-4"
                onClick={() => navigate(`/chat/${f.conversation_id}`)}
              >
                <Avatar src={f.avatar_url} fallback={f.nickname?.[0] || '?'} size="md" ring />
                <div className="min-w-0 flex-1">
                  <p className="font-bold text-slate-900">{f.nickname}</p>
                  <p className="truncate text-xs text-slate-500">{f.school || f.major || '上海科技大学'}</p>
                </div>
                <Button size="sm" variant="ghost">
                  <MessageCircle className="h-4 w-4" />
                </Button>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
