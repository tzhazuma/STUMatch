import { useNavigate } from 'react-router-dom';
import { MapPin, GraduationCap, Heart, Star, UserPlus } from 'lucide-react';
import { Button } from './ui/Button';
import { Avatar } from './ui/Avatar';
import { Badge } from './ui/Badge';
import type { DiscoveryItem, Section } from '@/types';

interface UserCardProps {
  user: DiscoveryItem;
  section: Section;
  onAddFriend: (user: DiscoveryItem) => void;
}

const tagColors = [
  'bg-brand-50 text-brand-700',
  'bg-sky-50 text-sky-700',
  'bg-emerald-50 text-emerald-700',
  'bg-amber-50 text-amber-700',
  'bg-rose-50 text-rose-700',
  'bg-violet-50 text-violet-700',
];

export function UserCard({ user, section, onAddFriend }: UserCardProps) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/discovery/${section}/${user.user_id}`)}
      className="card flex cursor-pointer gap-4 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-soft"
    >
      <div className="flex-shrink-0">
        <Avatar src={user.avatar_url} alt={user.nickname} size="lg" fallback={user.nickname?.[0] || '?'} ring />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="truncate text-base font-bold text-slate-900">{user.nickname}</h3>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              {user.age && <span className="rounded-md bg-slate-100 px-2 py-0.5">{user.age} 岁</span>}
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
          </div>
          {typeof user.match_score === 'number' && (
            <Badge className="shrink-0 bg-gradient-to-r from-brand-500 to-accent-500 text-white shadow-sm">
              <Star className="mr-0.5 h-3 w-3 fill-current" />
              {Math.round(user.match_score * 100)}%
            </Badge>
          )}
        </div>

        {section === 'academic' && user.major && (
          <p className="mt-2 truncate text-xs text-slate-600">
            <span className="font-semibold text-brand-600">专业</span> · {user.major}
          </p>
        )}
        {section === 'dating' && (
          <p className="mt-2 truncate text-xs text-slate-600">
            <Heart className="mr-0.5 inline h-3 w-3 text-rose-400" />
            {user.match_reason || '缘分相遇'}
          </p>
        )}
        {user.bio && (
          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-500">{user.bio}</p>
        )}

        {user.interests && user.interests.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {user.interests.slice(0, 5).map((tag, idx) => (
              <span
                key={tag}
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${tagColors[idx % tagColors.length]}`}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="mt-4 flex justify-end">
          <Button
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onAddFriend(user);
            }}
          >
            <UserPlus className="mr-1 h-3.5 w-3.5" />
            加好友
          </Button>
        </div>
      </div>
    </div>
  );
}
