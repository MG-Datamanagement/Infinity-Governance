import { z } from 'zod';

// Auth Schemas
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Invalid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
});

export const registerSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .min(2, 'Name must be at least 2 characters')
    .max(50, 'Name must be less than 50 characters'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Invalid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

// Search Schema
export const searchSchema = z.object({
  query: z
    .string()
    .min(1, 'Search query is required')
    .max(200, 'Search query too long')
    .refine((val) => val.trim().length > 0, 'Search query cannot be empty'),
});

// Compliance Issue Schema
export const complianceIssueSchema = z.object({
  issue: z
    .string()
    .min(1, 'Issue description is required')
    .max(500, 'Description too long'),
  framework: z
    .string()
    .min(1, 'Framework is required'),
  severity: z.enum(['HIGH', 'MEDIUM', 'LOW'], {
    errorMap: () => ({ message: 'Invalid severity level' }),
  }),
  dataset: z
    .string()
    .min(1, 'Dataset is required')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Invalid dataset name'),
  assignee: z
    .string()
    .min(1, 'Assignee is required'),
  dueDate: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date format (YYYY-MM-DD)'),
});

// Data Source Schema
export const dataSourceSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name too long'),
  type: z.enum(['PostgreSQL', 'MySQL', 'MongoDB', 'Snowflake', 'BigQuery'], {
    errorMap: () => ({ message: 'Invalid data source type' }),
  }),
  host: z
    .string()
    .min(1, 'Host is required')
    .max(255, 'Host too long'),
  port: z
    .number()
    .int()
    .min(1, 'Port must be greater than 0')
    .max(65535, 'Port must be less than 65536'),
  database: z
    .string()
    .min(1, 'Database name is required')
    .max(100, 'Database name too long'),
  username: z
    .string()
    .min(1, 'Username is required')
    .max(100, 'Username too long'),
  password: z
    .string()
    .min(1, 'Password is required'),
});

// Generic API Query Schema
export const apiQuerySchema = z.object({
  page: z.number().int().min(1).optional().default(1),
  limit: z.number().int().min(1).max(100).optional().default(10),
  sortBy: z.string().optional(),
  sortOrder: z.enum(['asc', 'desc']).optional().default('desc'),
  search: z.string().max(200).optional(),
});

// Type exports
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type SearchInput = z.infer<typeof searchSchema>;
export type ComplianceIssueInput = z.infer<typeof complianceIssueSchema>;
export type DataSourceInput = z.infer<typeof dataSourceSchema>;
export type ApiQueryInput = z.infer<typeof apiQuerySchema>;
