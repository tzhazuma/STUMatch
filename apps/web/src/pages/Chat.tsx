import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { getMessages, sendMessage } from '@/api/endpoints';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import type { Message } from '@/types';
import { Send, Loader2 } from 'lucide-react';

export default function Chat() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const { connected, messages: wsMessages, send } = useWebSocket();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!conversationId) return;
    setLoading(true);
    getMessages(conversationId, { page: 1, limit: 50 })
      .then((res) => setMessages(res.items))
      .finally(() => setLoading(false));
  }, [conversationId]);

  useEffect(() => {
    if (wsMessages.length) {
      const last = wsMessages[wsMessages.length - 1];
      if (last.conversation_id === conversationId) {
        setMessages((prev) => [...prev, last]);
      }
    }
  }, [wsMessages, conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!text.trim() || !conversationId) return;
    if (connected) {
      send({
        type: 'send_message',
        payload: { conversation_id: conversationId, content: text, message_type: 'text' },
      });
    } else {
      await sendMessage(conversationId, text);
      const res = await getMessages(conversationId, { page: 1, limit: 50 });
      setMessages(res.items);
    }
    setText('');
  };

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col animate-fade-in">
      <div className="flex-1 overflow-y-auto rounded-3xl border border-slate-100 bg-white p-4 shadow-card scrollbar-hide">
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
            <p className="text-sm">加载消息中...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-slate-400">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
              <Send className="h-6 w-6" />
            </div>
            <p className="text-sm">开始聊天吧</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((m, idx) => {
              const isMe = m.sender_id === user?.id;
              const showTime =
                idx === 0 ||
                new Date(m.created_at).getTime() - new Date(messages[idx - 1].created_at).getTime() > 5 * 60 * 1000;
              return (
                <div key={m.id}>
                  {showTime && (
                    <p className="mb-3 text-center text-[10px] text-slate-400">
                      {new Date(m.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </p>
                  )}
                  <div className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                        isMe
                          ? 'bg-gradient-to-br from-brand-500 to-brand-600 text-white rounded-br-md'
                          : 'bg-slate-100 text-slate-800 rounded-bl-md'
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-2 rounded-2xl border border-slate-100 bg-white/80 p-2 shadow-soft backdrop-blur">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="输入消息..."
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="border-0 bg-transparent shadow-none focus:ring-0"
        />
        <Button onClick={handleSend} className="rounded-xl px-4">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
