import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}

const Card = ({ children, className, title, subtitle }: CardProps) => {
  return (
    <div className={cn(
      'rounded-lg border border-gray-200 bg-white shadow-sm',
      className
    )}>
      {(title || subtitle) && (
        <div className="p-6 pb-4">
          {title && (
            <h3 className="text-xl font-semibold leading-none tracking-tight text-black">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-600 mt-1">
              {subtitle}
            </p>
          )}
        </div>
      )}
      <div className={cn(title || subtitle ? 'px-6 pb-6' : 'p-6')}>
        {children}
      </div>
    </div>
  );
};

const CardHeader = ({ children, className }: { children: ReactNode; className?: string }) => {
  return (
    <div className={cn('flex flex-col space-y-1.5 p-6', className)}>
      {children}
    </div>
  );
};

const CardTitle = ({ children, className }: { children: ReactNode; className?: string }) => {
  return (
    <h3 className={cn('text-xl font-semibold leading-none tracking-tight text-black', className)}>
      {children}
    </h3>
  );
};

const CardDescription = ({ children, className }: { children: ReactNode; className?: string }) => {
  return (
    <p className={cn('text-sm text-gray-600', className)}>
      {children}
    </p>
  );
};

const CardContent = ({ children, className }: { children: ReactNode; className?: string }) => {
  return (
    <div className={cn('p-6 pt-0', className)}>
      {children}
    </div>
  );
};

export { Card, CardHeader, CardTitle, CardDescription, CardContent };
