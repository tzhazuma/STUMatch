import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { getMyProfile, updateProfile, uploadAvatar, getMyReferralCode } from '@/api/endpoints';
import type { Profile } from '@/types';
import { Camera, Copy, CheckCircle, Gift, Edit3, User, Heart, BookOpen } from 'lucide-react';

const educationOptions = [
  { value: '', label: '请选择' },
  { value: 'undergraduate', label: '本科' },
  { value: 'master', label: '硕士' },
  { value: 'phd', label: '博士' },
  { value: 'other', label: '其他' },
];

const genderOptions = [
  { value: '', label: '请选择' },
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'other', label: '其他' },
];

const questionnaireLinks = [
  { slug: 'basic', label: '基础资料', icon: User, color: 'bg-brand-50 text-brand-700' },
  { slug: 'academic', label: '学术交流', icon: BookOpen, color: 'bg-sky-50 text-sky-700' },
  { slug: 'daily', label: '日常生活', icon: Edit3, color: 'bg-emerald-50 text-emerald-700' },
  { slug: 'dating', label: '恋爱交友', icon: Heart, color: 'bg-rose-50 text-rose-700' },
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [referral, setReferral] = useState<{ code: string; link: string } | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getMyProfile(),
      getMyReferralCode().catch(() => null),
    ])
      .then(([p, r]) => {
        setProfile(p);
        if (r) setReferral({ code: r.code, link: r.link });
      })
      .finally(() => setLoading(false));
  }, []);

  const updateField = (field: keyof Profile, value: string | string[]) => {
    if (!profile) return;
    setProfile({ ...profile, [field]: value });
  };

  const handleAvatar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profile) return;
    const res = await uploadAvatar(file);
    setProfile({ ...profile, avatar_url: res.avatar_url });
  };

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await updateProfile({
        nickname: profile.nickname,
        gender: profile.gender,
        birth_date: profile.birth_date,
        education_level: profile.education_level,
        major: profile.major,
        mbti: profile.mbti,
        interests: profile.interests,
        location: profile.location,
        bio: profile.bio,
        research_direction: profile.research_direction,
        dating_purpose: profile.dating_purpose,
        family_status: profile.family_status,
        ideal_person: profile.ideal_person,
      });
      setProfile(updated);
      setMessage('保存成功');
      setTimeout(() => setMessage(''), 2000);
    } catch (e: any) {
      setMessage(e?.response?.data?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
      <p className="text-sm">加载中...</p>
    </div>
  );
  if (!profile) return <p className="py-20 text-center text-sm text-slate-400">暂无资料</p>;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header card */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-500 to-accent-500 p-6 text-white shadow-elevated">
        <div className="relative z-10 flex items-center gap-4">
          <div className="relative">
            {profile.avatar_url ? (
              <img src={profile.avatar_url} alt="avatar" className="h-20 w-20 rounded-full object-cover ring-4 ring-white/30" />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/20 text-2xl font-bold ring-4 ring-white/30">
                {profile.nickname?.[0] || '?'}
              </div>
            )}
            <label className="absolute bottom-0 right-0 flex h-7 w-7 cursor-pointer items-center justify-center rounded-full bg-white text-brand-600 shadow-md transition hover:bg-slate-100">
              <Camera className="h-3.5 w-3.5" />
              <input type="file" accept="image/*" className="hidden" onChange={handleAvatar} />
            </label>
          </div>
          <div>
            <h1 className="text-xl font-extrabold">{profile.nickname}</h1>
            <div className="mt-1.5 flex items-center gap-2">
              <Badge className="bg-white/20 text-white border-0">
                {profile.is_verified_email ? (
                  <><CheckCircle className="mr-1 h-3 w-3" /> 已验证</>
                ) : (
                  '未验证'
                )}
              </Badge>
              <span className="text-xs text-white/80">{profile.school || '上海科技大学'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Questionnaire shortcuts */}
      <div className="grid grid-cols-2 gap-3">
        {questionnaireLinks.map((q) => {
          const Icon = q.icon;
          return (
            <a
              key={q.slug}
              href={`/questionnaire/${q.slug}`}
              onClick={(e) => {
                e.preventDefault();
                window.location.href = `/questionnaire/${q.slug}`;
              }}
              className="flex items-center gap-3 rounded-2xl bg-white p-3 shadow-card transition hover:shadow-soft"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${q.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-800">{q.label}</p>
                <p className="text-[10px] text-slate-400">点击填写</p>
              </div>
            </a>
          );
        })}
      </div>

      {/* Basic info */}
      <Card>
        <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">
          <User className="h-4 w-4 text-brand-500" />
          基本信息
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="昵称" value={profile.nickname || ''} onChange={(e) => updateField('nickname', e.target.value)} />
          <Select
            label="性别"
            options={genderOptions}
            value={profile.gender || ''}
            onChange={(e) => updateField('gender', e.target.value)}
          />
          <Input
            label="出生日期"
            type="date"
            value={profile.birth_date || ''}
            onChange={(e) => updateField('birth_date', e.target.value)}
          />
          <Select
            label="学历"
            options={educationOptions}
            value={profile.education_level || ''}
            onChange={(e) => updateField('education_level', e.target.value)}
          />
          <Input label="专业" value={profile.major || ''} onChange={(e) => updateField('major', e.target.value)} />
          <Input label="MBTI" value={profile.mbti || ''} onChange={(e) => updateField('mbti', e.target.value)} />
          <Input label="现居地" value={profile.location || ''} onChange={(e) => updateField('location', e.target.value)} />
          <Input
            label="兴趣爱好（逗号分隔）"
            value={profile.interests?.join(',') || ''}
            onChange={(e) => updateField('interests', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
          />
        </div>
      </Card>

      {/* Academic */}
      <Card>
        <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">
          <BookOpen className="h-4 w-4 text-sky-500" />
          学术方向
        </h2>
        <Textarea
          label="想要学术交流的方向"
          value={profile.research_direction || ''}
          onChange={(e) => updateField('research_direction', e.target.value)}
        />
      </Card>

      {/* Dating */}
      <Card>
        <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">
          <Heart className="h-4 w-4 text-rose-500" />
          交友信息
        </h2>
        <div className="space-y-4">
          <Textarea label="交友目的" value={profile.dating_purpose || ''} onChange={(e) => updateField('dating_purpose', e.target.value)} />
          <Textarea label="想遇见的人" value={profile.ideal_person || ''} onChange={(e) => updateField('ideal_person', e.target.value)} />
          <Textarea label="家庭状况（选填）" value={profile.family_status || ''} onChange={(e) => updateField('family_status', e.target.value)} />
        </div>
      </Card>

      {/* Bio */}
      <Card>
        <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">
          <Edit3 className="h-4 w-4 text-emerald-500" />
          个人介绍
        </h2>
        <Textarea label="自我介绍" value={profile.bio || ''} onChange={(e) => updateField('bio', e.target.value)} rows={4} />
        {message && (
          <p className={`mt-3 text-sm font-medium ${message.includes('成功') ? 'text-emerald-600' : 'text-red-500'}`}>
            {message}
          </p>
        )}
        <Button onClick={handleSave} isLoading={saving} className="mt-4 w-full">
          保存资料
        </Button>
      </Card>

      {/* Referral */}
      <Card className="border-brand-100 bg-gradient-to-br from-brand-50/50 to-white">
        <h2 className="mb-3 flex items-center gap-2 text-base font-bold text-slate-900">
          <Gift className="h-4 w-4 text-brand-500" />
          邀请好友
        </h2>
        {referral ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl bg-white p-3 shadow-sm">
              <div>
                <p className="text-xs text-slate-500">你的邀请码</p>
                <p className="text-lg font-black tracking-widest text-brand-600">{referral.code}</p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(referral.code);
                  setMessage('邀请码已复制');
                  setTimeout(() => setMessage(''), 2000);
                }}
              >
                <Copy className="mr-1 h-3.5 w-3.5" />
                复制
              </Button>
            </div>
            <Button
              type="button"
              variant="primary"
              className="w-full"
              onClick={() => {
                navigator.clipboard.writeText(referral.link);
                setMessage('邀请链接已复制');
                setTimeout(() => setMessage(''), 2000);
              }}
            >
              复制邀请链接
            </Button>
          </div>
        ) : (
          <p className="text-sm text-slate-500">加载邀请信息失败</p>
        )}
      </Card>
    </div>
  );
}
