import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../store/authStore';
import { API } from '../api/endpoints';

export default function LoginScreen() {
  const navigation = useNavigation();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('上海科技大学');
  const [loading, setLoading] = useState(false);
  const [codeSent, setCodeSent] = useState(false);
  const { setAuth } = useAuthStore();

  const sendCode = async () => {
    if (!email) return;
    setLoading(true);
    try {
      await API.auth.sendCode(email, mode === 'register' ? 'register' : 'login');
      setCodeSent(true);
      Alert.alert('验证码已发送，请在控制台/日志查看');
    } catch (e: any) {
      Alert.alert('发送失败', e?.message || '未知错误');
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    setLoading(true);
    try {
      let res;
      if (mode === 'login') {
        res = await API.auth.login(email, password);
      } else {
        res = await API.auth.register({ email, code, password, nickname, school });
      }
      setAuth(res, res.user);
    } catch (e: any) {
      Alert.alert('失败', e?.response?.data?.message || e?.message || '未知错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>UniMatch</Text>
      <Text style={styles.subtitle}>校园同行匹配</Text>

      <View style={styles.tabRow}>
        <TouchableOpacity
          style={[styles.tab, mode === 'login' && styles.tabActive]}
          onPress={() => setMode('login')}
        >
          <Text style={mode === 'login' ? styles.tabTextActive : styles.tabText}>登录</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, mode === 'register' && styles.tabActive]}
          onPress={() => setMode('register')}
        >
          <Text style={mode === 'register' ? styles.tabTextActive : styles.tabText}>注册</Text>
        </TouchableOpacity>
      </View>

      <TextInput
        style={styles.input}
        placeholder="邮箱"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      {mode === 'register' && (
        <>
          <View style={styles.codeRow}>
            <TextInput
              style={[styles.input, { flex: 1 }]}
              placeholder="验证码"
              value={code}
              onChangeText={setCode}
              keyboardType="number-pad"
            />
            <TouchableOpacity style={styles.codeBtn} onPress={sendCode} disabled={loading}>
              {loading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.codeBtnText}>{codeSent ? '已发送' : '发送'}</Text>
              )}
            </TouchableOpacity>
          </View>
          <TextInput style={styles.input} placeholder="昵称" value={nickname} onChangeText={setNickname} />
          <TextInput style={styles.input} placeholder="学校" value={school} onChangeText={setSchool} />
        </>
      )}
      <TextInput
        style={styles.input}
        placeholder="密码"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity style={styles.button} onPress={submit} disabled={loading}>
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>{mode === 'login' ? '登录' : '注册'}</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center', backgroundColor: '#fff' },
  title: { fontSize: 32, fontWeight: 'bold', color: '#6366f1', textAlign: 'center' },
  subtitle: { textAlign: 'center', color: '#6b7280', marginBottom: 24 },
  tabRow: { flexDirection: 'row', backgroundColor: '#f3f4f6', borderRadius: 8, padding: 4, marginBottom: 16 },
  tab: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: 6 },
  tabActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 2 },
  tabText: { color: '#6b7280' },
  tabTextActive: { color: '#6366f1', fontWeight: '600' },
  input: {
    borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 16,
  },
  codeRow: { flexDirection: 'row', gap: 8 },
  codeBtn: { backgroundColor: '#6366f1', paddingHorizontal: 16, borderRadius: 8, justifyContent: 'center' },
  codeBtnText: { color: '#fff', fontWeight: '600' },
  button: { backgroundColor: '#6366f1', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
