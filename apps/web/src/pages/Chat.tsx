import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { getMessages, sendMessage } from '@/api/endpoints';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import { errorMessage, toast } from '@/components/ui/Toast';
import type { Message } from '@/types';
import { Send, Loader2 } from 'lucide-react';

export default function Chat() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Merge an inbound WS message into the current list: drop a matching
  // optimistic placeholder (same sender + content) and de-duplicate by id.
  const mergeIncoming = useCallback(
    (msg: Message) => {
      if (!conversationId || msg.conversation_id !== conversationId) return;
      setMessages((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev;
        const withoutPlaceholder = prev.filter(
          (m) =>
            !(
              m._pending &&
              m.sender_id === msg.sender_id &&
              m.content === msg.content
            )
        );
        return [...withoutPlaceholder, msg];
      });
    },
    [conversationId]
  );

  const handleWsMessage = useCallback(
    (data: Record<string, unknown>) => {
      if (data.type === 'new_message') {
        const msg = (data.message ?? data.payload) as Message | undefined;
        if (msg) mergeIncoming(msg);
      } else if (data.type === 'error') {
        toast.error(typeof data.message === 'string' ? data.message : '发送失败');
      }
    },
    [mergeIncoming]
  );

  const { connected, send } = useWebSocket({ onMessage: handleWsMessage });

  useEffect(() => {
    if (!conversationId) return;
    setLoading(true);
    getMessages(conversationId, { page: 1, limit: 50 })
      .then((res) => setMessages(res.items))
      .catch(() => toast.error('加载消息失败'))
      .finally(() => setLoading(false));
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const content = text.trim();
    if (!content || !conversationId) return;
    setText('');

    const placeholder: Message = {
      id: `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      conversation_id: conversationId,
      sender_id: user?.id || '',
      content,
      message_type: 'text',
      created_at: new Date().toISOString(),
      _pending: true,
    };
    setMessages((prev) => [...prev, placeholder]);

    if (connected) {
      const ok = send({
        type: 'send_message',
        payload: { conversation_id: conversationId, content, message_type: 'text' },
      });
      if (!ok) {
        // Socket closed between the check and send — fall back to REST.
        await sendViaRest(conversationId, content, placeholder.id);
      }
      // When WS is up the server echoes the message back to us (and the peer),
      // which mergeIncoming turns into the confirmed message.
    } else {
      await sendViaRest(conversationId, content, placeholder.id);
    }
  };

  const sendViaRest = async (convId: string, content: string, placeholderId: string) => {
    try {
      const saved = await sendMessage(convId, content);
      setMessages((prev) => prev.map((m) => (m.id === placeholderId ? { ...saved, _pending: false } : m)));
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== placeholderId));
      toast.error(errorMessage(e, '消息发送失败'));
    }
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
                      } ${m._pending ? 'opacity-60' : ''}`}
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
