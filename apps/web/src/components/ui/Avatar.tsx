import React from 'react';

interface AvatarProps {
  src?: string;
  alt?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  fallback?: string;
}

export function Avatar({ src, alt = '', size = 'md', fallback = '?' }: AvatarProps) {
  const sizes = { sm: 'h-8 w-8 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-16 w-16 text-lg', xl: 'h-24 w-24 text-2xl' };
  return (
    <div className={`${sizes[size]} flex-shrink-0 overflow-hidden rounded-full bg-gray-200 flex items-center justify-center text-gray-500 font-medium`}>
      {src ? <img src={src} alt={alt} className="h-full w-full object-cover" /> : fallback}
    </div>
  );
}
