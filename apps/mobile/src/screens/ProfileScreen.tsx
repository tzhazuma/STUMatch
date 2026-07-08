import { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { API } from '../api/endpoints';
import type { Profile } from '../types';

export default function ProfileScreen() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    API.profile.getMyProfile().then((p) => { setProfile(p); setLoading(false); });
  }, []);

  const update = (field: keyof Profile, value: string | string[]) => {
    if (!profile) return;
    setProfile({ ...profile, [field]: value });
  };

  const pickAvatar = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (!result.canceled && profile) {
      const uri = result.assets[0].uri;
      const form = new FormData();
      form.append('file', {
        uri,
        name: 'avatar.jpg',
        type: 'image/jpeg',
      } as any);
      const res = await API.profile.uploadAvatar(form);
      setProfile({ ...profile, avatar_url: res.avatar_url });
    }
  };

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await API.profile.updateMyProfile({
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
        ideal_person: profile.ideal_person,
        family_status: profile.family_status,
      });
      setProfile(updated);
      Alert.alert('保存成功');
    } catch (e: any) {
      Alert.alert('保存失败', e?.response?.data?.message || e?.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!profile) return <View style={styles.center}><Text>暂无资料</Text></View>;

  return (
    <ScrollView style={styles.container}>
      <TouchableOpacity style={styles.avatarWrap} onPress={pickAvatar}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{profile.nickname?.[0] || '?'}</Text>
        </View>
        <Text style={styles.avatarHint}>点击更换头像</Text>
      </TouchableOpacity>

      <Text style={styles.label}>昵称</Text>
      <TextInput style={styles.input} value={profile.nickname} onChangeText={(t) => update('nickname', t)} />

      <Text style={styles.label}>性别</Text>
      <TextInput style={styles.input} value={profile.gender || ''} onChangeText={(t) => update('gender', t)} />

      <Text style={styles.label}>出生日期</Text>
      <TextInput style={styles.input} value={profile.birth_date || ''} placeholder="YYYY-MM-DD" onChangeText={(t) => update('birth_date', t)} />

      <Text style={styles.label}>学历</Text>
      <TextInput style={styles.input} value={profile.education_level || ''} onChangeText={(t) => update('education_level', t)} />

      <Text style={styles.label}>专业</Text>
      <TextInput style={styles.input} value={profile.major || ''} onChangeText={(t) => update('major', t)} />

      <Text style={styles.label}>MBTI</Text>
      <TextInput style={styles.input} value={profile.mbti || ''} onChangeText={(t) => update('mbti', t)} />

      <Text style={styles.label}>兴趣爱好（逗号分隔）</Text>
      <TextInput
        style={styles.input}
        value={profile.interests?.join(',') || ''}
        onChangeText={(t) => update('interests', t.split(',').map((s) => s.trim()).filter(Boolean))}
      />

      <Text style={styles.label}>现居地</Text>
      <TextInput style={styles.input} value={profile.location || ''} onChangeText={(t) => update('location', t)} />

      <Text style={styles.label}>个人介绍</Text>
      <TextInput style={styles.input} value={profile.bio || ''} onChangeText={(t) => update('bio', t)} multiline />

      <Text style={styles.label}>学术方向</Text>
      <TextInput style={styles.input} value={profile.research_direction || ''} onChangeText={(t) => update('research_direction', t)} />

      <Text style={styles.label}>交友目的</Text>
      <TextInput style={styles.input} value={profile.dating_purpose || ''} onChangeText={(t) => update('dating_purpose', t)} />

      <Text style={styles.label}>想遇见的人</Text>
      <TextInput style={styles.input} value={profile.ideal_person || ''} onChangeText={(t) => update('ideal_person', t)} />

      <Text style={styles.label}>家庭状况</Text>
      <TextInput style={styles.input} value={profile.family_status || ''} onChangeText={(t) => update('family_status', t)} />

      <TouchableOpacity style={styles.btn} onPress={save} disabled={saving}>
        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>保存</Text>}
      </TouchableOpacity>
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  avatarWrap: { alignItems: 'center', marginBottom: 16 },
  avatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#e0e7ff', alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 28, fontWeight: 'bold', color: '#6366f1' },
  avatarHint: { marginTop: 8, color: '#6366f1', fontSize: 12 },
  label: { fontSize: 14, color: '#374151', marginTop: 12, marginBottom: 4 },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, padding: 10, fontSize: 15 },
  btn: { backgroundColor: '#6366f1', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 20 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
