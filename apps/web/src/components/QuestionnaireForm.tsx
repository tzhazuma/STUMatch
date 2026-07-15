import { useState } from 'react';
import { Star } from 'lucide-react';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Textarea } from './ui/Textarea';
import { Card } from './ui/Card';
import type { Questionnaire, Question } from '@/types';

export const SAMPLE_QUESTIONNAIRES: Questionnaire[] = [
  {
    slug: 'basic',
    title: '基础资料',
    description: '完善你的基础信息，让更多人认识你。',
    section: 'global',
    questions: [
      { id: 'nickname', text: '昵称', type: 'text', required: true },
      { id: 'school', text: '学校', type: 'text', required: true },
      { id: 'gender', text: '性别', type: 'single_choice', required: true, options: [{ value: 'male', label: '男' }, { value: 'female', label: '女' }, { value: 'other', label: '其他' }] },
      { id: 'birth_date', text: '出生日期', type: 'text', required: false },
      { id: 'education_level', text: '学历', type: 'single_choice', required: true, options: [{ value: 'undergraduate', label: '本科' }, { value: 'master', label: '硕士' }, { value: 'phd', label: '博士' }, { value: 'other', label: '其他' }] },
    ],
  },
  {
    slug: 'academic',
    title: '学术交流问卷',
    description: '填写研究方向和兴趣，匹配更合适的学术伙伴。',
    section: 'academic',
    questions: [
      { id: 'major', text: '专业', type: 'text', required: true },
      { id: 'research_direction', text: '研究方向', type: 'text', required: true },
      { id: 'interests', text: '学术兴趣标签（空格分隔）', type: 'tags', required: true },
      { id: 'research_rating', text: '科研热情评分', type: 'rating', required: true, max: 5, min: 1 },
    ],
  },
  {
    slug: 'daily',
    title: '日常生活问卷',
    description: '让我们了解你的生活习惯和兴趣。',
    section: 'daily',
    questions: [
      { id: 'mbti', text: 'MBTI', type: 'single_choice', required: true, options: ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP'].map(v => ({ value: v, label: v })) },
      { id: 'interests', text: '兴趣爱好（空格分隔）', type: 'tags', required: true },
      { id: 'location', text: '常驻地', type: 'text', required: true },
      { id: 'bio', text: '自我介绍', type: 'text', required: false },
    ],
  },
  {
    slug: 'dating',
    title: '恋爱交友问卷',
    description: '描述你的理想另一半，开启缘分匹配。',
    section: 'dating',
    questions: [
      { id: 'dating_purpose', text: '交友目的', type: 'single_choice', required: true, options: [{ value: 'serious', label: '认真恋爱' }, { value: 'casual', label: '先做朋友' }, { value: 'marriage', label: '结婚' }, { value: 'other', label: '其他' }] },
      { id: 'location', text: '所在城市', type: 'text', required: true },
      { id: 'ideal_person', text: '理想伴侣', type: 'text', required: false },
      { id: 'family_status', text: '家庭状况', type: 'text', required: false },
      { id: 'dating_rating', text: '脱单意愿', type: 'rating', required: true, max: 5, min: 1 },
    ],
  },
];

interface QuestionnaireFormProps {
  questionnaire: Questionnaire;
  initialAnswers?: Record<string, unknown>;
  onSubmit: (answers: Record<string, unknown>) => void | Promise<void>;
  isSubmitting?: boolean;
}

export function QuestionnaireForm({ questionnaire, initialAnswers = {}, onSubmit, isSubmitting }: QuestionnaireFormProps) {
  const [answers, setAnswers] = useState<Record<string, unknown>>(initialAnswers);

  const set = (id: string, value: unknown) => setAnswers((prev) => ({ ...prev, [id]: value }));

  const toggleMulti = (id: string, value: string) => {
    const current = (answers[id] as string[] | undefined) || [];
    if (current.includes(value)) {
      set(id, current.filter((v) => v !== value));
    } else {
      set(id, [...current, value]);
    }
  };

  const addTag = (id: string, value: string) => {
    const current = ((answers[id] as string[]) || []).map(s => s.trim()).filter(Boolean);
    if (value && !current.includes(value)) {
      set(id, [...current, value]);
    }
  };

  const removeTag = (id: string, tag: string) => {
    const current = (answers[id] as string[] | undefined) || [];
    set(id, current.filter((t) => t !== tag));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(answers);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">{questionnaire.title}</h1>
        {questionnaire.description && <p className="text-sm text-gray-500">{questionnaire.description}</p>}
      </div>
      {questionnaire.questions.map((q) => (
        <Card key={q.id}>
          <label className="mb-2 block text-sm font-medium text-gray-800">
            {q.text}
            {q.required && <span className="ml-1 text-red-500">*</span>}
          </label>
          <QuestionInput
            question={q}
            value={answers[q.id]}
            onChange={(v) => set(q.id, v)}
            onToggle={(v) => toggleMulti(q.id, v)}
            onAddTag={(v) => addTag(q.id, v)}
            onRemoveTag={(v) => removeTag(q.id, v)}
          />
        </Card>
      ))}
      <Button type="submit" isLoading={isSubmitting} className="w-full">
        提交问卷
      </Button>
    </form>
  );
}

function QuestionInput({
  question,
  value,
  onChange,
  onToggle,
  onAddTag,
  onRemoveTag,
}: {
  question: Question;
  value: unknown;
  onChange: (v: unknown) => void;
  onToggle: (v: string) => void;
  onAddTag: (v: string) => void;
  onRemoveTag: (v: string) => void;
}) {
  const [tagInput, setTagInput] = useState('');
  const tags = ((value as string[] | undefined) || []).filter(Boolean);

  if (question.type === 'single_choice') {
    return (
      <div className="flex flex-wrap gap-2">
        {question.options?.map((opt) => (
          <label
            key={opt.value}
            className={`cursor-pointer rounded-lg border px-3 py-2 text-sm transition ${
              value === opt.value ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
          >
            <input type="radio" name={question.id} value={opt.value} checked={value === opt.value} onChange={() => onChange(opt.value)} className="sr-only" />
            {opt.label}
          </label>
        ))}
      </div>
    );
  }

  if (question.type === 'multiple_choice') {
    return (
      <div className="flex flex-wrap gap-2">
        {question.options?.map((opt) => {
          const selected = ((value as string[] | undefined) || []).includes(opt.value);
          return (
            <label
              key={opt.value}
              className={`cursor-pointer rounded-lg border px-3 py-2 text-sm transition ${
                selected ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-gray-200 bg-white hover:bg-gray-50'
              }`}
            >
              <input type="checkbox" checked={selected} onChange={() => onToggle(opt.value)} className="sr-only" />
              {opt.label}
            </label>
          );
        })}
      </div>
    );
  }

  if (question.type === 'rating') {
    const max = question.max || 5;
    const rating = Number(value || 0);
    return (
      <div className="flex items-center gap-1">
        {Array.from({ length: max }).map((_, i) => (
          <button type="button" key={i} onClick={() => onChange(i + 1)} className="p-1">
            <Star className={`h-6 w-6 ${i < rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
          </button>
        ))}
      </div>
    );
  }

  if (question.type === 'tags') {
    return (
      <div>
        <div className="flex gap-2">
          <Input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onAddTag(tagInput);
                setTagInput('');
              }
            }}
            placeholder="输入后按空格或回车"
          />
          <Button type="button" variant="secondary" size="sm" onClick={() => { onAddTag(tagInput); setTagInput(''); }}>
            添加
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span key={tag} className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-xs text-brand-700">
              {tag}
              <button type="button" onClick={() => onRemoveTag(tag)} className="text-brand-700 hover:text-brand-900">×</button>
            </span>
          ))}
        </div>
      </div>
    );
  }

  // text
  if ((question.text || '').length > 30) {
    return <Textarea value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} rows={3} />;
  }
  return <Input value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} />;
}
