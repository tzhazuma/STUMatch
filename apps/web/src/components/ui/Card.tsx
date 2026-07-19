import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  hover?: boolean;
}

export function Card({ children, className = '', hover = false, ...props }: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-slate-100 bg-white p-5 shadow-card ${
        hover ? 'transition-all duration-300 hover:-translate-y-0.5 hover:shadow-soft' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
