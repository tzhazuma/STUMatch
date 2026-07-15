import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { API } from '../api/endpoints';

type DocType = 'terms' | 'privacy';

interface LegalDoc {
  title: string;
  content: string;
  updated_at: string;
}

export default function LegalScreen() {
  const route = useRoute<any>();
  const navigation = useNavigation<any>();
  const doc: DocType = route.params?.doc === 'privacy' ? 'privacy' : 'terms';

  const [data, setData] = useState<LegalDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    API.legal
      .get(doc)
      .then((d) => {
        setData(d);
        navigation.setOptions({ title: d.title });
      })
      .catch((e: any) => {
        setError(e?.response?.data?.message || e?.message || '加载失败');
      })
      .finally(() => setLoading(false));
  }, [doc, navigation]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error || '文档不存在'}</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>{data.title}</Text>
      <Text style={styles.updated}>
        最后更新：{new Date(data.updated_at).toLocaleDateString('zh-CN')}
      </Text>
      <Text style={styles.body}>{data.content}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 20, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  title: { fontSize: 22, fontWeight: 'bold', color: '#111827', marginBottom: 8 },
  updated: { fontSize: 12, color: '#9ca3af', marginBottom: 16 },
  body: { fontSize: 14, lineHeight: 22, color: '#374151' },
  error: { color: '#ef4444', fontSize: 14 },
});
