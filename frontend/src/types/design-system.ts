/**
 * Design system type definitions for type-safe token usage
 */

export type ThemeColor =
  | 'primary'
  | 'primary-hover'
  | 'primary-light'
  | 'primary-dark'
  | 'positive'
  | 'positive-light'
  | 'positive-dark'
  | 'negative'
  | 'negative-light'
  | 'negative-dark';

export type TypographyScale =
  | 'heading-xl'
  | 'heading-lg'
  | 'heading-md'
  | 'value-primary'
  | 'value-secondary';

export type SpacingToken =
  | 'container-padding-x'
  | 'container-padding-y'
  | 'card-padding'
  | 'card-gap';

export type ShadowToken = 'card' | 'card-hover';

export type RadiusToken = 'card' | 'button' | 'input';

/**
 * Example usage in components:
 *
 * ```tsx
 * import { cn } from '@/utils/cn';
 *
 * // Using color tokens
 * const buttonClass = cn(
 *   'bg-primary hover:bg-primary-hover',
 *   'text-white',
 *   'rounded-button',
 *   'px-6 py-4',
 *   'shadow-card hover:shadow-card-hover'
 * );
 *
 * // Using typography tokens
 * const headingClass = cn('text-heading-xl', 'text-foreground-primary');
 *
 * // Using spacing tokens
 * const containerClass = cn('px-container-padding-x', 'py-container-padding-y');
 *
 * // Using semantic colors for financial data
 * const valueClass = cn(
 *   'text-value-primary',
 *   dailyChange >= 0 ? 'text-positive' : 'text-negative'
 * );
 * ```
 */
