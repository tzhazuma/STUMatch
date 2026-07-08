import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { listFriends, listFriendRequests, acceptFriendRequest, rejectFriendRequest } from '@/api/endpoints';
import type { Friend, FriendRequest } from '@/types';

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

  if (loading) return <p className="text-center text-sm text-gray-500">加载中...</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">好友</h1>
      {requests.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-gray-500">好友申请</h2>
          {requests.map((req) => (
            <Card key={req.id} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{req.from_user?.nickname || '用户'}</p>
                <p className="text-xs text-gray-500">{req.message || '想加你为好友'}</p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleAccept(req.id)}>接受</Button>
                <Button size="sm" variant="secondary" onClick={() => handleReject(req.id)}>拒绝</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <h2 className="text-sm font-medium text-gray-500">我的好友</h2>
        {friends.length === 0 ? (
          <p className="text-sm text-gray-400">还没有好友</p>
        ) : (
          friends.map((f) => (
            <Card
              key={f.user_id}
              className="flex cursor-pointer items-center gap-3"
              onClick={() => navigate(`/chat/${f.conversation_id}`)}
            >
              {f.avatar_url ? (
                <img src={f.avatar_url} alt="avatar" className="h-10 w-10 rounded-full" />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-600">
                  {f.nickname?.[0] || '?'}
                </div>
              )}
              <div>
                <p className="font-medium">{f.nickname}</p>
                <p className="text-xs text-gray-500">{f.school || f.major || ''}</p>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
