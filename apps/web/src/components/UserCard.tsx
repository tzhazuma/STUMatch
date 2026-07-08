import { useNavigate } from 'react-router-dom';
import { MapPin, GraduationCap, Heart, Star } from 'lucide-react';
import { Button } from './ui/Button';
import { Avatar } from './ui/Avatar';
import { Badge } from './ui/Badge';
import type { DiscoveryItem, Section } from '@/types';

interface UserCardProps {
  user: DiscoveryItem;
  section: Section;
  onAddFriend: (user: DiscoveryItem) => void;
}

export function UserCard({ user, section, onAddFriend }: UserCardProps) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/discovery/${section}/${user.user_id}`)}
      className="card flex cursor-pointer gap-4 p-4 transition hover:shadow-md"
    >
      <Avatar src={user.avatar_url} alt={user.nickname} size="lg" fallback={user.nickname?.[0] || '?'} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="truncate text-base font-semibold">{user.nickname}</h3>
          {typeof user.match_score === 'number' && (
            <Badge variant="info" className="flex items-center gap-1">
              <Star className="h-3 w-3" />
              {Math.round(user.match_score * 100)}%
            </Badge>
          )}
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
          {user.age && <span>{user.age} 岁</span>}
          {user.education_level && (
            <span className="flex items-center gap-0.5">
              <GraduationCap className="h-3 w-3" />
              {user.education_level}
            </span>
          )}
          {user.location && (
            <span className="flex items-center gap-0.5">
              <MapPin className="h-3 w-3" />
              {user.location}
            </span>
          )}
        </div>

        {section === 'academic' && user.major && (
          <p className="mt-1 truncate text-xs text-gray-600">专业：{user.major}</p>
        )}
        {section === 'dating' && (
          <p className="mt-1 truncate text-xs text-gray-600">
            <Heart className="mr-0.5 inline h-3 w-3" />
            {user.match_reason || '缘分相遇'}
          </p>
        )}
        {user.interests && user.interests.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {user.interests.slice(0, 5).map((tag) => (
              <span key={tag} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="mt-3 flex justify-end">
          <Button
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onAddFriend(user);
            }}
          >
            加好友
          </Button>
        </div>
      </div>
    </div>
  );
}
