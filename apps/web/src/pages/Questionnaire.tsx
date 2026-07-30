import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { QuestionnaireForm } from '@/components/QuestionnaireForm';
import { getQuestionnaire, submitQuestionnaire, getMyResponse } from '@/api/endpoints';
import { errorMessage, toast } from '@/components/ui/Toast';
import type { Questionnaire } from '@/types';

export default function QuestionnairePage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    Promise.all([getQuestionnaire(slug), getMyResponse(slug)])
      .then(([q, r]) => {
        setQuestionnaire(q);
        if (r?.answers) setAnswers(r.answers);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const handleSubmit = async (data: Record<string, unknown>) => {
    if (!slug) return;
    setSubmitting(true);
    try {
      await submitQuestionnaire(slug, { answers: data });
      toast.success('提交成功');
      navigate('/profile');
    } catch (e) {
      toast.error(errorMessage(e, '提交失败'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="text-center text-sm text-gray-500">加载中...</p>;
  if (!questionnaire) return <p className="text-center text-sm text-gray-500">问卷不存在</p>;

  return (
    <QuestionnaireForm
      questionnaire={questionnaire}
      initialAnswers={answers}
      onSubmit={handleSubmit}
      isSubmitting={submitting}
    />
  );
}
