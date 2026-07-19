import React from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, children, footer }: ModalProps) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md rounded-3xl bg-white p-6 shadow-elevated">
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="text-lg font-bold text-slate-900">{title}</h3>}
          <button onClick={onClose} className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="text-sm leading-relaxed text-slate-600">{children}</div>
        {footer && <div className="mt-6 flex items-center justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
