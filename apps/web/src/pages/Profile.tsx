import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { Card } from '@/components/ui/Card';
import { getMyProfile, updateProfile, uploadAvatar } from '@/api/endpoints';
import type { Profile } from '@/types';

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

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setLoading(true);
    getMyProfile()
      .then(setProfile)
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
    } catch (e: any) {
      setMessage(e?.response?.data?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-center text-sm text-gray-500">加载中...</p>;
  if (!profile) return <p className="text-center text-sm text-gray-500">暂无资料</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">个人资料</h1>
      <Card>
        <div className="flex items-center gap-4">
          <div className="relative">
            {profile.avatar_url ? (
              <img src={profile.avatar_url} alt="avatar" className="h-20 w-20 rounded-full object-cover" />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-600">
                {profile.nickname?.[0] || '?'}
              </div>
            )}
            <label className="absolute bottom-0 right-0 rounded-full bg-brand-600 px-2 py-1 text-xs text-white shadow hover:bg-brand-700">
              修改
              <input type="file" accept="image/*" className="hidden" onChange={handleAvatar} />
            </label>
          </div>
          <div>
            <p className="font-semibold">{profile.nickname}</p>
            <p className="text-xs text-gray-500">
              {profile.is_verified_email ? '邮箱已验证' : '邮箱未验证'}
            </p>
          </div>
        </div>
      </Card>

      <Card className="space-y-4">
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
        <Input
          label="兴趣爱好（逗号分隔）"
          value={profile.interests?.join(',') || ''}
          onChange={(e) => updateField('interests', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
        />
        <Input label="现居地" value={profile.location || ''} onChange={(e) => updateField('location', e.target.value)} />
        <Textarea label="个人介绍" value={profile.bio || ''} onChange={(e) => updateField('bio', e.target.value)} />
        <Textarea
          label="想要学术交流的方向"
          value={profile.research_direction || ''}
          onChange={(e) => updateField('research_direction', e.target.value)}
        />
        <Textarea
          label="交友目的"
          value={profile.dating_purpose || ''}
          onChange={(e) => updateField('dating_purpose', e.target.value)}
        />
        <Textarea
          label="想遇见的人"
          value={profile.ideal_person || ''}
          onChange={(e) => updateField('ideal_person', e.target.value)}
        />
        <Textarea
          label="家庭状况（选填）"
          value={profile.family_status || ''}
          onChange={(e) => updateField('family_status', e.target.value)}
        />
        {message && <p className="text-sm text-brand-600">{message}</p>}
        <Button onClick={handleSave} isLoading={saving} className="w-full">
          保存
        </Button>
      </Card>
    </div>
  );
}
