import { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import { API } from '../api/endpoints';
import type { DiscoveryUserDetail, Section } from '../types';
import { RootScreenProps } from '../navigation/types';

export default function UserDetailScreen() {
  const route = useRoute<RootScreenProps<'UserDetail'>['route']>();
  const { section, userId } = route.params;
  const [user, setUser] = useState<DiscoveryUserDetail | null>(null);

  useEffect(() => {
    API.discovery.getUser(section as Section, userId).then(setUser);
  }, [section, userId]);

  const handleAddFriend = async () => {
    try {
      await API.friends.sendRequest(userId, '想认识你');
      Alert.alert('好友申请已发送');
    } catch (e: any) {
      Alert.alert('失败', e?.response?.data?.message || '发送失败');
    }
  };

  if (!user) {
    return (
      <View style={styles.center}>
        <Text>加载中...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user.nickname?.[0] || '?'}</Text>
        </View>
        <View>
          <Text style={styles.name}>{user.nickname}</Text>
          <Text style={styles.meta}>
            {user.age && `${user.age}岁 · `}
            {user.education_level}
            {user.location ? ` · ${user.location}` : ''}
          </Text>
          {user.match_reason && <Text style={styles.reason}>{user.match_reason}</Text>}
        </View>
      </View>

      <View style={styles.section}>
        {section === 'academic' && (
          <>
            <Text style={styles.row}>专业：{user.major || '未填写'}</Text>
            <Text style={styles.row}>学术方向：{user.research_direction || '未填写'}</Text>
          </>
        )}
        {section === 'daily' && (
          <>
            <Text style={styles.row}>MBTI：{user.mbti || '未填写'}</Text>
            <Text style={styles.row}>个人介绍：{user.bio || '未填写'}</Text>
          </>
        )}
        {section === 'dating' && (
          <>
            <Text style={styles.row}>交友目的：{user.dating_purpose || '未填写'}</Text>
            <Text style={styles.row}>想遇见的人：{user.ideal_person || '未填写'}</Text>
            <Text style={styles.row}>家庭状况：{user.family_status || '未填写'}</Text>
          </>
        )}
        <Text style={styles.row}>兴趣：{user.interests?.join(' · ') || '未填写'}</Text>
      </View>

      <TouchableOpacity style={styles.btn} onPress={handleAddFriend}>
        <Text style={styles.btnText}>加好友</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', gap: 16, backgroundColor: '#fff', padding: 16, borderRadius: 12 },
  avatar: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#e0e7ff', alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 28, fontWeight: 'bold', color: '#6366f1' },
  name: { fontSize: 20, fontWeight: 'bold' },
  meta: { color: '#6b7280', marginTop: 4 },
  reason: { color: '#6366f1', marginTop: 4 },
  section: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginTop: 12 },
  row: { fontSize: 15, marginBottom: 8, color: '#374151' },
  btn: { backgroundColor: '#6366f1', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 16 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
