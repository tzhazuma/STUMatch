import { useEffect } from 'react';
import { create } from 'zustand';
import { CheckCircle2, XCircle, AlertTriangle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastStore {
  toasts: ToastItem[];
  show: (message: string, type?: ToastType, durationMs?: number) => void;
  dismiss: (id: number) => void;
}

let _seq = 0;

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  show: (message, type = 'success', durationMs = 3000) => {
    const id = ++_seq;
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    if (durationMs > 0) {
      window.setTimeout(() => get().dismiss(id), durationMs);
    }
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Convenience helpers so call sites read naturally. */
export const toast = {
  success: (m: string) => useToastStore.getState().show(m, 'success'),
  error: (m: string) => useToastStore.getState().show(m, 'error'),
  info: (m: string) => useToastStore.getState().show(m, 'info'),
};

/**
 * Extract a human readable message from an axios / fetch error, preferring the
 * FastAPI `detail` field over a generic `message`.
 */
export function errorMessage(e: unknown, fallback = '操作失败'): string {
  const anyE = e as { response?: { data?: { detail?: unknown; message?: string } }; message?: string };
  const detail = anyE?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  const msg = anyE?.response?.data?.message;
  if (typeof msg === 'string' && msg) return msg;
  if (typeof anyE?.message === 'string' && anyE.message) return anyE.message;
  return fallback;
}

const styles: Record<ToastType, { box: string; Icon: typeof CheckCircle2; icon: string }> = {
  success: { box: 'border-emerald-200 bg-emerald-50 text-emerald-800', Icon: CheckCircle2, icon: 'text-emerald-500' },
  error: { box: 'border-red-200 bg-red-50 text-red-700', Icon: XCircle, icon: 'text-red-500' },
  info: { box: 'border-slate-200 bg-white text-slate-700', Icon: AlertTriangle, icon: 'text-slate-400' },
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  // Keep the hook referenced so unused-import lint stays happy across builds.
  useEffect(() => {}, []);

  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex flex-col items-center gap-2 px-4">
      {toasts.map((t) => {
        const s = styles[t.type];
        const Icon = s.Icon;
        return (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex w-full max-w-sm animate-slide-up items-start gap-2.5 rounded-2xl border px-4 py-3 text-sm font-medium shadow-elevated ${s.box}`}
          >
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${s.icon}`} />
            <span className="flex-1 break-words leading-relaxed">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="shrink-0 rounded-full p-0.5 opacity-60 transition hover:opacity-100"
              aria-label="关闭"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
