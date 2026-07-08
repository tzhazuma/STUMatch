import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Card({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`rounded-xl border border-gray-100 bg-white p-4 shadow-sm ${className}`} {...props}>
      {children}
    </div>
  );
}
