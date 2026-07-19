import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <label className="block w-full">
        {label && <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>}
        <input
          ref={ref}
          className={`w-full rounded-xl border bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition-all placeholder:text-slate-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-100 ${
            error ? 'border-red-500 focus:border-red-500 focus:ring-red-100' : 'border-slate-200'
          } ${className}`}
          {...props}
        />
        {error && <span className="mt-1.5 block text-xs text-red-500">{error}</span>}
      </label>
    );
  }
);
Input.displayName = 'Input';
