import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Sparkles, BookOpen, Coffee, Heart, ShieldCheck, Zap, Users } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-full bg-slate-50">
      {/* Hero */}
      <section className="relative overflow-hidden px-4 pb-20 pt-12">
        <div className="absolute -left-20 -top-20 h-72 w-72 rounded-full bg-brand-200/40 blur-3xl" />
        <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-accent-200/30 blur-3xl" />

        <div className="relative z-10 mx-auto max-w-2xl text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
            <Sparkles className="h-10 w-10 text-white" />
          </div>
          <h1 className="text-4xl font-black leading-tight text-slate-900 sm:text-5xl">
            SKDMatch <span className="text-gradient">科爱捏</span>
          </h1>
          <p className="mx-auto mt-4 max-w-md text-lg font-medium text-slate-500">
            校内互助交流平台 · 让上科大同学轻松找到学术伙伴、生活搭子与心动对象
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link to="/register">
              <Button size="lg">立即加入</Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="secondary">已有账号登录</Button>
            </Link>
          </div>

          <div className="mt-6 flex items-center justify-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5 text-brand-500" /> 实名校园认证</span>
            <span className="flex items-center gap-1"><Zap className="h-3.5 w-3.5 text-accent-500" /> 智能匹配推荐</span>
            <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5 text-sky-500" /> 三大交流场景</span>
          </div>
        </div>
      </section>

      {/* Scenes */}
      <section className="px-4 pb-24">
        <div className="mx-auto max-w-2xl">
          <h2 className="mb-8 text-center text-2xl font-extrabold text-slate-900">三大匹配场景</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <SceneCard
              icon={BookOpen}
              title="学术交流"
              desc="找到同方向的研究伙伴，组队做项目、找导师、聊论文。"
              color="from-brand-500 to-brand-400"
            />
            <SceneCard
              icon={Coffee}
              title="日常生活"
              desc="寻找饭搭子、运动伙伴、自习室友，让校园生活更有趣。"
              color="from-sky-500 to-sky-400"
            />
            <SceneCard
              icon={Heart}
              title="恋爱交友"
              desc="基于问卷与兴趣的真实匹配，在校园里遇见心动的 TA。"
              color="from-rose-500 to-rose-400"
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-8 text-center text-xs text-slate-400">
        <p>© 2026 SKDMatch 科爱捏 · 上科大互助交流平台</p>
        <div className="mt-2 flex justify-center gap-4">
          <Link to="/legal/terms" className="hover:text-slate-600">用户服务协议</Link>
          <Link to="/legal/privacy" className="hover:text-slate-600">隐私保护协议</Link>
        </div>
      </footer>
    </div>
  );
}

function SceneCard({
  icon: Icon,
  title,
  desc,
  color,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
  color: string;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-soft">
      <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${color} shadow-md`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-lg font-bold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">{desc}</p>
    </div>
  );
}
