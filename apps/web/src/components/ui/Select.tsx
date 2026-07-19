import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className = '', ...props }, ref) => {
    return (
      <label className="block w-full">
        {label && <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>}
        <select
          ref={ref}
          className={`w-full rounded-xl border bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition-all focus:border-brand-400 focus:ring-4 focus:ring-brand-100 ${
            error ? 'border-red-500 focus:border-red-500 focus:ring-red-100' : 'border-slate-200'
          } ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <span className="mt-1.5 block text-xs text-red-500">{error}</span>}
      </label>
    );
  }
);
Select.displayName = 'Select';
