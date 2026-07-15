import { Loader2 } from 'lucide-react';

export function Loading({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-500">
      <Loader2 className="h-8 w-8 animate-spin" />
      <span className="mt-2 text-sm">{text}</span>
    </div>
  );
}
