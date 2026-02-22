import * as React from 'react';
import { cn } from '../../lib/utils';

type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive';
type ButtonSize = 'default' | 'sm' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  default: 'ui-button ui-button-default',
  secondary: 'ui-button ui-button-secondary',
  outline: 'ui-button ui-button-outline',
  ghost: 'ui-button ui-button-ghost',
  destructive: 'ui-button ui-button-destructive',
};

const sizeClasses: Record<ButtonSize, string> = {
  default: 'ui-button-md',
  sm: 'ui-button-sm',
  lg: 'ui-button-lg',
};

export function Button({
  className,
  variant = 'default',
  size = 'default',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(variantClasses[variant], sizeClasses[size], className)}
      {...props}
    />
  );
}

