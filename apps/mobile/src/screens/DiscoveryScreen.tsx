import { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { API } from '../api/endpoints';
import { RootNavigationProp } from '../navigation/types';
import type { DiscoveryItem, Section, Profile } from '../types';

const sections: { key: Section; label: string }[] = [
  { key: 'academic', label: '学术交流' },
  { key: 'daily', label: '日常生活' },
  { key: 'dating', label: '恋爱交友' },
];

export default function DiscoveryScreen() {
  const navigation = useNavigation<RootNavigationProp>();
  const [section, setSection] = useState<Section>('academic');
  const [users, setUsers] = useState<DiscoveryItem[]>([]);
  const [q, setQ] = useState('');
  const [push, setPush] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    API.profile.getMyProfile().then(setProfile).catch(() => {});
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [section, q, push]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await API.discovery.discover(section, { q, push, page: 1, limit: 20 });
      setUsers(res.items);
    } finally {
      setLoading(false);
    }
  };

  const handlePush = async () => {
    if (!profile?.is_verified_email) {
      Alert.alert('完善交友资料，开启精确匹配', '请先完成邮箱验证并完善资料');
      return;
    }
    const enabled = !push;
    await API.discovery.setPush(section, enabled);
    setPush(enabled);
  };

  const handleAddFriend = async (user: DiscoveryItem) => {
    if (!profile?.is_verified_email) {
      Alert.alert('完善交友资料，开启精确匹配', '请先完成邮箱验证并完善资料');
      return;
    }
    try {
      await API.friends.sendRequest(user.user_id, '想认识你');
      Alert.alert('好友申请已发送');
    } catch (e: any) {
      Alert.alert('失败', e?.response?.data?.message || '发送失败');
    }
  };

  const renderItem = ({ item }: { item: DiscoveryItem }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => navigation.navigate('UserDetail', { section, userId: item.user_id })}
    >
      {item.avatar_url ? (
        <Image source={{ uri: item.avatar_url }} style={styles.avatar} />
      ) : (
        <View style={[styles.avatar, { backgroundColor: '#e0e7ff', alignItems: 'center', justifyContent: 'center' }]}>
          <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#6366f1' }}>
            {item.nickname?.[0] || '?'}
          </Text>
        </View>
      )}
      <View style={{ flex: 1 }}>
        <Text style={styles.name}>{item.nickname}</Text>
        <Text style={styles.meta}>
          {item.age && `${item.age}岁 `}
          {item.education_level}
          {item.major ? ` · ${item.major}` : ''}
        </Text>
        {item.interests && item.interests.length > 0 && (
          <Text style={styles.tags}>{item.interests.slice(0, 5).join(' · ')}</Text>
        )}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.btn} onPress={() => handleAddFriend(item)}>
            <Text style={styles.btnText}>加好友</Text>
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.tabs}>
        {sections.map((s) => (
          <TouchableOpacity
            key={s.key}
            style={[styles.tab, section === s.key && styles.tabActive]}
            onPress={() => setSection(s.key)}
          >
            <Text style={section === s.key ? styles.tabTextActive : styles.tabText}>{s.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.searchRow}>
        <TextInput
          style={styles.input}
          placeholder="搜索昵称、专业..."
          value={q}
          onChangeText={setQ}
          onSubmitEditing={fetchUsers}
        />
        <TouchableOpacity style={[styles.pushBtn, push && styles.pushBtnActive]} onPress={handlePush}>
          <Text style={styles.pushBtnText}>{push ? '已推送' : '开启推送'}</Text>
        </TouchableOpacity>
      </View>
      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={users}
          keyExtractor={(item) => item.user_id}
          renderItem={renderItem}
          contentContainerStyle={{ paddingBottom: 16 }}
          ListEmptyComponent={<Text style={styles.empty}>暂无用户</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 8, padding: 4, marginBottom: 12 },
  tab: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  tabActive: { backgroundColor: '#6366f1' },
  tabText: { color: '#6b7280' },
  tabTextActive: { color: '#fff', fontWeight: '600' },
  searchRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  input: {
    flex: 1, borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, padding: 10, backgroundColor: '#fff',
  },
  pushBtn: { backgroundColor: '#e5e7eb', paddingHorizontal: 12, borderRadius: 8, justifyContent: 'center' },
  pushBtnActive: { backgroundColor: '#6366f1' },
  pushBtnText: { color: '#374151', fontWeight: '500' },
  card: { flexDirection: 'row', gap: 12, backgroundColor: '#fff', padding: 12, borderRadius: 12, marginBottom: 10 },
  avatar: { width: 56, height: 56, borderRadius: 28 },
  name: { fontSize: 16, fontWeight: '600' },
  meta: { color: '#6b7280', fontSize: 12, marginTop: 2 },
  tags: { color: '#9ca3af', fontSize: 12, marginTop: 4 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 8 },
  btn: { backgroundColor: '#6366f1', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6 },
  btnText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  empty: { textAlign: 'center', color: '#9ca3af', marginTop: 24 },
});
