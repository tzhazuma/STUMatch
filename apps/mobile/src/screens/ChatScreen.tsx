import { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import { API } from '../api/endpoints';
import { useAuthStore } from '../store/authStore';
import { RootScreenProps } from '../navigation/types';
import type { Message } from '../types';

export default function ChatScreen() {
  const route = useRoute<RootScreenProps<'Chat'>['route']>();
  const { conversationId, participant } = route.params;
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    API.chat.getMessages(conversationId, { page: 1, limit: 50 }).then((res) => {
      setMessages(res.items);
      setLoading(false);
    });
  }, [conversationId]);

  const send = async () => {
    if (!text.trim()) return;
    const msg = await API.chat.sendMessage(conversationId, text);
    setMessages((prev) => [...prev, msg]);
    setText('');
  };

  const renderItem = ({ item }: { item: Message }) => (
    <View
      style={[
        styles.bubble,
        item.sender_id === user?.id ? styles.myBubble : styles.otherBubble,
      ]}
    >
      <Text style={item.sender_id === user?.id ? styles.myText : styles.otherText}>
        {item.content}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.header}>{participant.nickname}</Text>
      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={renderItem}
          contentContainerStyle={{ padding: 12 }}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />
      )}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={setText}
          placeholder="输入消息..."
        />
        <TouchableOpacity style={styles.sendBtn} onPress={send}>
          <Text style={styles.sendBtnText}>发送</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: { padding: 16, fontSize: 18, fontWeight: 'bold', textAlign: 'center', backgroundColor: '#fff' },
  bubble: { maxWidth: '75%', padding: 10, borderRadius: 12, marginBottom: 8 },
  myBubble: { alignSelf: 'flex-end', backgroundColor: '#6366f1' },
  otherBubble: { alignSelf: 'flex-start', backgroundColor: '#fff' },
  myText: { color: '#fff' },
  otherText: { color: '#1f2937' },
  inputRow: { flexDirection: 'row', padding: 12, backgroundColor: '#fff', gap: 8 },
  input: { flex: 1, borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, padding: 10 },
  sendBtn: { backgroundColor: '#6366f1', paddingHorizontal: 16, borderRadius: 8, justifyContent: 'center' },
  sendBtnText: { color: '#fff', fontWeight: '600' },
});
