interface AvatarProps {
  src?: string;
  alt?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  fallback?: string;
  ring?: boolean;
}

export function Avatar({ src, alt = '', size = 'md', fallback = '?', ring = false }: AvatarProps) {
  const sizes = {
    sm: 'h-9 w-9 text-xs',
    md: 'h-11 w-11 text-sm',
    lg: 'h-16 w-16 text-lg',
    xl: 'h-24 w-24 text-2xl',
  };
  return (
    <div
      className={`${sizes[size]} flex-shrink-0 overflow-hidden rounded-full bg-gradient-to-br from-brand-100 to-brand-50 flex items-center justify-center font-semibold text-brand-600 ${
        ring ? 'ring-2 ring-white shadow-md' : ''
      }`}
    >
      {src ? (
        <img src={src} alt={alt} className="h-full w-full object-cover" />
      ) : (
        fallback
      )}
    </div>
  );
}
