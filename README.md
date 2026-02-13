# Infinity Governance

Production-ready data governance and compliance platform with proper authentication, validation, and error handling.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **Authentication**: NextAuth.js with bcrypt
- **Validation**: Zod
- **Error Handling**: React Error Boundary
- **Charts**: Recharts
- **Icons**: Lucide React

## Features

✅ **Proper Authentication**
- Bcrypt password hashing
- Zod validation on login
- Secure session management
- JWT tokens with NextAuth

✅ **Input Validation**
- Zod schemas for all forms
- Client-side validation
- Server-side validation
- Detailed error messages

✅ **Error Boundaries & Fallbacks**
- Global error boundary
- Component-level error boundaries
- Loading states
- Network error handling
- Data error fallbacks
- Empty state components

✅ **Dashboard Features**
- Real-time compliance monitoring
- AI governance snapshot
- Compliance trends visualization
- Issue tracking

✅ **Development Ready**
- Mock API with simulated delays
- REST/GraphQL switchable architecture
- Responsive design
- Modular components

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:

```bash
npm install
```

2. Environment variables are already configured in `.env.local`:

```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here-change-in-production
```

⚠️ **IMPORTANT**: Change `NEXTAUTH_SECRET` before production deployment!

3. Run development server:

```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000)

### Demo Credentials

**Admin User:**
- Email: `shivam@infinity.com`
- Password: `password`

**Regular User:**
- Email: `rajkumar@infinity.com`
- Password: `password123`

## Project Structure

```
src/
├── app/
│   ├── (auth)/login/         # Login with Zod validation
│   ├── (dashboard)/          # Protected dashboard routes
│   │   ├── overview/         # Overview page with error boundaries
│   │   └── compliance/       # Compliance page with error boundaries
│   ├── api/auth/             # NextAuth with bcrypt
│   └── layout.tsx            # Root layout with error boundary
├── components/
│   ├── layout/               # Sidebar, Header
│   ├── ui/                   # Reusable UI components
│   ├── charts/               # Chart components
│   ├── compliance/           # Compliance components
│   ├── ErrorBoundary.tsx     # Global error boundary
│   └── Fallbacks.tsx         # Loading & error fallbacks
├── lib/
│   ├── validations.ts        # Zod schemas
│   ├── auth/userDb.ts        # User database with bcrypt
│   ├── api-client.ts         # API client
│   └── utils.ts              # Utilities
├── hooks/                    # React Query hooks
├── services/                 # API services
├── store/                    # Zustand store
├── types/                    # TypeScript types
└── constants/                # Mock data
```

## Security Features

### Authentication
- Password hashing with bcrypt (10 rounds)
- JWT session tokens
- Secure cookie handling
- Session expiration (30 days)

### Input Validation
All user inputs are validated with Zod:
- Email format validation
- Password strength requirements
- Length constraints
- Type checking
- Custom validation rules

### Error Handling
- Error boundaries prevent app crashes
- Graceful degradation
- User-friendly error messages
- Development error details
- Retry mechanisms

## Validation Schemas

Located in `src/lib/validations.ts`:

- `loginSchema` - Login form validation
- `registerSchema` - User registration (future)
- `searchSchema` - Search input validation
- `complianceIssueSchema` - Issue creation
- `dataSourceSchema` - Data source configuration
- `apiQuerySchema` - API query parameters

## Error Boundaries

### Global Error Boundary
Wraps entire app in `app/layout.tsx`

### Component Error Boundaries
- Each major page section
- Individual data components
- Chart components

### Fallback Components
- `LoadingFallback` - Loading spinner
- `ErrorFallback` - Generic error
- `NetworkErrorFallback` - Network issues
- `DataErrorFallback` - Data loading errors
- `EmptyState` - No data available

## API Architecture

Flexible API client supporting REST and GraphQL:

```typescript
// lib/api-client.ts
apiClient.setAPIType('rest'); // or 'graphql'

// Usage
const data = await apiClient.get('/endpoint');
```

Currently using mock data with simulated network delays.

## Available Scripts

```bash
npm run dev         # Development server
npm run build       # Production build
npm run start       # Production server
npm run lint        # ESLint
npm run type-check  # TypeScript check
```

## Environment Variables

Required for production:

```env
NEXTAUTH_URL=https://your-domain.com
NEXTAUTH_SECRET=<generate-secure-random-string>
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

Generate secure secret:
```bash
openssl rand -base64 32
```

## Mock Data

Currently using mock data from `src/constants/mockData.ts`

To switch to real API:
1. Update `src/services/api/`
2. Configure `NEXT_PUBLIC_API_URL`
3. Update React Query hooks

## What's Production-Ready

✅ **Implemented:**
- Proper authentication with bcrypt
- Input validation with Zod
- Error boundaries & fallbacks
- Loading states
- Type safety
- Responsive design
- Modular architecture

⚠️ **Still Needed for Production:**
- Real backend API integration
- Database connection
- Rate limiting
- Security headers (CSP, CORS)
- Logging & monitoring (Sentry)
- Unit & E2E tests
- Performance optimization
- SEO optimization
- Deployment configuration

## Development Notes

### Adding New Validated Form

1. Create Zod schema in `lib/validations.ts`:
```typescript
export const myFormSchema = z.object({
  field: z.string().min(1, 'Required'),
});
```

2. Use in component:
```typescript
const validatedData = myFormSchema.parse(formData);
```

### Adding Error Boundary

Wrap component:
```typescript
<ErrorBoundary fallback={<CustomFallback />}>
  <YourComponent />
</ErrorBoundary>
```

### Creating New User

```typescript
// In development
await userDb.createUser({
  name: 'John Doe',
  email: 'john@example.com',
  password: 'securePassword123',
  role: 'user'
});
```

## Best Practices Implemented

1. **Never trust user input** - All inputs validated
2. **Fail gracefully** - Error boundaries everywhere
3. **Security first** - Passwords hashed, JWT secure
4. **Type safety** - Full TypeScript coverage
5. **User feedback** - Loading states, error messages
6. **Code organization** - Modular, scalable structure

## Migration from Mock to Real API

1. Implement API endpoints
2. Update `src/services/api/`
3. Replace mock service calls
4. Configure environment variables
5. Test authentication flow
6. Update error handling for real errors

## Support & Documentation

- See `STRUCTURE.md` for architecture details
- Check `QUICKSTART.md` for quick setup
- Review Zod docs for validation: https://zod.dev
- NextAuth docs: https://next-auth.js.org

## License

Private - Infinity Governance
