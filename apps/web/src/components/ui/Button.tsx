import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'accent';
  isLoading?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = 'primary', isLoading, size = 'md', className = '', ...props }, ref) => {
    const base = 'inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]';
    const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2.5 text-sm', lg: 'px-6 py-3.5 text-base' };
    const variants = {
      primary: 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-soft hover:from-brand-700 hover:to-brand-600 hover:shadow-elevated focus:ring-brand-500',
      secondary: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 hover:shadow-sm focus:ring-brand-500',
      accent: 'bg-gradient-to-r from-accent-500 to-accent-400 text-white shadow-soft hover:from-accent-600 hover:to-accent-500 focus:ring-accent-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
      ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 focus:ring-slate-300',
    };
    return (
      <button ref={ref} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
