import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { getMessages, sendMessage } from '@/api/endpoints';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import type { Message } from '@/types';

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
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <Card className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <p className="text-center text-sm text-gray-500">加载中...</p>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-2 text-sm ${
                    m.sender_id === user?.id
                      ? 'bg-brand-600 text-white'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>
      <div className="mt-2 flex gap-2">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="输入消息..."
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="flex-1"
        />
        <Button onClick={handleSend}>发送</Button>
      </div>
    </div>
  );
}
