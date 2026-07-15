import React from 'react';

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(({ label, ...props }, ref) => {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <div className="relative">
        <input ref={ref} type="checkbox" className="peer sr-only" {...props} />
        <div className="h-6 w-10 rounded-full bg-gray-300 transition peer-checked:bg-brand-600" />
        <div className="absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition peer-checked:translate-x-4" />
      </div>
      {label && <span className="text-sm text-gray-700">{label}</span>}
    </label>
  );
});
Switch.displayName = 'Switch';
