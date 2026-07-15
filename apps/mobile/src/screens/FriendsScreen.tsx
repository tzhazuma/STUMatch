import { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { API } from '../api/endpoints';
import { RootNavigationProp } from '../navigation/types';
import type { Friend, FriendRequest } from '../types';

export default function FriendsScreen() {
  const navigation = useNavigation<RootNavigationProp>();
  const [friends, setFriends] = useState<Friend[]>([]);
  const [requests, setRequests] = useState<FriendRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    setLoading(true);
    try {
      const [f, r] = await Promise.all([
        API.friends.getFriends(),
        API.friends.getRequests('received'),
      ]);
      setFriends(f);
      setRequests(r);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const accept = async (id: string) => {
    await API.friends.acceptRequest(id);
    fetch();
  };

  const reject = async (id: string) => {
    await API.friends.rejectRequest(id);
    fetch();
  };

  const renderRequest = ({ item }: { item: FriendRequest }) => (
    <View style={styles.card}>
      <Text style={styles.name}>好友申请</Text>
      <Text style={styles.meta}>{item.message || '想加你为好友'}</Text>
      <View style={styles.row}>
        <TouchableOpacity style={styles.btn} onPress={() => accept(item.id)}>
          <Text style={styles.btnText}>接受</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={() => reject(item.id)}>
          <Text style={styles.btnTextSecondary}>拒绝</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderFriend = ({ item }: { item: Friend }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => {
        Alert.alert('聊天功能', '请在网页端或后续版本体验实时聊天');
      }}
    >
      <Text style={styles.name}>{item.nickname}</Text>
      <Text style={styles.meta}>{item.school || item.major || ''}</Text>
    </TouchableOpacity>
  );

  if (loading) return <View style={styles.center}><ActivityIndicator /></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>好友</Text>
      {requests.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>好友申请</Text>
          <FlatList data={requests} keyExtractor={(i) => i.id} renderItem={renderRequest} />
        </>
      )}
      <Text style={styles.sectionTitle}>我的好友</Text>
      <FlatList
        data={friends}
        keyExtractor={(i) => i.user_id}
        renderItem={renderFriend}
        ListEmptyComponent={<Text style={styles.empty}>还没有好友</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 12 },
  sectionTitle: { fontSize: 14, color: '#6b7280', marginTop: 12, marginBottom: 8 },
  card: { backgroundColor: '#fff', padding: 12, borderRadius: 12, marginBottom: 10 },
  name: { fontSize: 16, fontWeight: '600' },
  meta: { color: '#6b7280', fontSize: 13, marginTop: 2 },
  row: { flexDirection: 'row', gap: 8, marginTop: 10 },
  btn: { backgroundColor: '#6366f1', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 6 },
  btnSecondary: { backgroundColor: '#e5e7eb' },
  btnText: { color: '#fff', fontWeight: '600' },
  btnTextSecondary: { color: '#374151', fontWeight: '600' },
  empty: { textAlign: 'center', color: '#9ca3af', marginTop: 24 },
});
