import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <label className="block w-full">
        {label && <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>}
        <textarea
          ref={ref}
          className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500 ${
            error ? 'border-red-500' : 'border-gray-300'
          } ${className}`}
          {...props}
        />
        {error && <span className="mt-1 block text-xs text-red-500">{error}</span>}
      </label>
    );
  }
);
Textarea.displayName = 'Textarea';
