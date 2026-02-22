import * as React from 'react';
import { cn } from '../../lib/utils';

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning';

const badgeClasses: Record<BadgeVariant, string> = {
  default: 'ui-badge ui-badge-default',
  secondary: 'ui-badge ui-badge-secondary',
  outline: 'ui-badge ui-badge-outline',
  success: 'ui-badge ui-badge-success',
  warning: 'ui-badge ui-badge-warning',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return <div className={cn(badgeClasses[variant], className)} {...props} />;
}
