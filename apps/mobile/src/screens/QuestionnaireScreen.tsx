import { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import { API } from '../api/endpoints';
import { RootScreenProps } from '../navigation/types';
import type { QuestionnaireDefinition, QuestionnaireQuestion } from '../types';

export default function QuestionnaireScreen() {
  const route = useRoute<RootScreenProps<'Questionnaire'>['route']>();
  const [slug, setSlug] = useState('basic');
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireDefinition | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    API.questionnaires.list().then((list) => {
      const first = list[0]?.slug || 'basic';
      setSlug(first);
      load(first);
    });
  }, []);

  const load = async (s: string) => {
    setLoading(true);
    const [q, r] = await Promise.all([
      API.questionnaires.get(s),
      API.questionnaires.getMyResponses(s).catch(() => null),
    ]);
    setQuestionnaire(q);
    if (r?.answers) setAnswers(r.answers);
    setLoading(false);
  };

  const [tagInput, setTagInput] = useState('');

  const setSingle = (id: string, value: string) => setAnswers({ ...answers, [id]: value });
  const toggleMulti = (id: string, value: string) => {
    const cur = (answers[id] as string[]) || [];
    if (cur.includes(value)) {
      setAnswers({ ...answers, [id]: cur.filter((v) => v !== value) });
    } else {
      setAnswers({ ...answers, [id]: [...cur, value] });
    }
  };
  const setText = (id: string, value: string) => setAnswers({ ...answers, [id]: value });
  const setRating = (id: string, value: number) => setAnswers({ ...answers, [id]: value });
  const addTag = (id: string, value: string) => {
    const text = value.trim();
    if (!text) return;
    const cur = (answers[id] as string[]) || [];
    if (!cur.includes(text)) {
      setAnswers({ ...answers, [id]: [...cur, text] });
    }
  };
  const removeTag = (id: string, value: string) => {
    const cur = (answers[id] as string[]) || [];
    setAnswers({ ...answers, [id]: cur.filter((v) => v !== value) });
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      await API.questionnaires.submit(slug, answers);
      Alert.alert('提交成功');
    } catch (e: any) {
      Alert.alert('提交失败', e?.response?.data?.message || e?.message);
    } finally {
      setSubmitting(false);
    }
  };

  const renderQuestion = (q: QuestionnaireQuestion) => (
    <View key={q.id} style={styles.qCard}>
      <Text style={styles.qText}>{q.text}{q.required && <Text style={{ color: 'red' }}> *</Text>}</Text>
      {q.type === 'single_choice' && (
        <View style={styles.options}>
          {q.options?.map((opt) => (
            <TouchableOpacity
              key={opt.value}
              style={[
                styles.option,
                answers[q.id] === opt.value && styles.optionSelected,
              ]}
              onPress={() => setSingle(q.id, opt.value)}
            >
              <Text style={answers[q.id] === opt.value ? styles.optionTextSelected : styles.optionText}>
                {opt.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
      {q.type === 'multiple_choice' && (
        <View style={styles.options}>
          {q.options?.map((opt) => {
            const selected = ((answers[q.id] as string[]) || []).includes(opt.value);
            return (
              <TouchableOpacity
                key={opt.value}
                style={[styles.option, selected && styles.optionSelected]}
                onPress={() => toggleMulti(q.id, opt.value)}
              >
                <Text style={selected ? styles.optionTextSelected : styles.optionText}>{opt.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
      {q.type === 'text' && (
        <TextInput
          style={styles.textInput}
          value={answers[q.id] || ''}
          onChangeText={(t) => setText(q.id, t)}
          multiline={q.text.length > 20}
        />
      )}
      {q.type === 'date' && (
        <TextInput
          style={styles.textInput}
          value={answers[q.id] || ''}
          onChangeText={(t) => setText(q.id, t)}
          placeholder="YYYY-MM-DD"
        />
      )}
      {q.type === 'rating' && (
        <View style={styles.ratingRow}>
          {Array.from({ length: q.max || 5 }).map((_, i) => (
            <TouchableOpacity key={i} onPress={() => setRating(q.id, i + 1)}>
              <Text style={i < (answers[q.id] || 0) ? styles.starActive : styles.star}>★</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
      {q.type === 'tags' && (
        <View>
          <View style={styles.tagInputRow}>
            <TextInput
              style={[styles.textInput, { flex: 1 }]}
              value={tagInput}
              onChangeText={setTagInput}
              placeholder="输入标签后添加"
              onSubmitEditing={() => { addTag(q.id, tagInput); setTagInput(''); }}
            />
            <TouchableOpacity style={styles.addTagBtn} onPress={() => { addTag(q.id, tagInput); setTagInput(''); }}>
              <Text style={styles.addTagText}>添加</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.tagRow}>
            {((answers[q.id] as string[]) || []).map((tag) => (
              <View key={tag} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
                <TouchableOpacity onPress={() => removeTag(q.id, tag)}>
                  <Text style={styles.tagRemove}> ×</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        </View>
      )}
    </View>
  );

  if (loading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!questionnaire) return <View style={styles.center}><Text>问卷不存在</Text></View>;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>{questionnaire.title}</Text>
      {questionnaire.description && <Text style={styles.desc}>{questionnaire.description}</Text>}
      {questionnaire.questions.map(renderQuestion)}
      <TouchableOpacity style={styles.submit} onPress={submit} disabled={submitting}>
        {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitText}>提交</Text>}
      </TouchableOpacity>
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 20, fontWeight: 'bold', marginBottom: 4 },
  desc: { color: '#6b7280', marginBottom: 16 },
  qCard: { backgroundColor: '#fff', padding: 12, borderRadius: 12, marginBottom: 12 },
  qText: { fontSize: 15, fontWeight: '500', marginBottom: 10 },
  options: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  option: { borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 },
  optionSelected: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
  optionText: { color: '#374151' },
  optionTextSelected: { color: '#fff' },
  textInput: { borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, padding: 10, minHeight: 44, textAlignVertical: 'top' },
  ratingRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  star: { fontSize: 28, color: '#d1d5db' },
  starActive: { fontSize: 28, color: '#fbbf24' },
  tagInputRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  addTagBtn: { backgroundColor: '#6366f1', borderRadius: 8, paddingHorizontal: 12, justifyContent: 'center' },
  addTagText: { color: '#fff', fontWeight: '600' },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  tag: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#e0e7ff', borderRadius: 16, paddingHorizontal: 10, paddingVertical: 4 },
  tagText: { color: '#4338ca', fontSize: 13 },
  tagRemove: { color: '#4338ca', fontSize: 16, marginLeft: 4 },
  submit: { backgroundColor: '#6366f1', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  submitText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
