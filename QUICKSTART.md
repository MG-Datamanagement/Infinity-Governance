# Quick Start Guide

## Setup (2 minutes)

```bash
cd infinity-governance
npm install
npm run dev
```

Open http://localhost:3000

## Login
- Email: `shivam@infinity.com`
- Password: `password`

## Available Routes
- `/login` - Authentication
- `/overview` - Dashboard overview (Screen 2)
- `/compliance` - Compliance monitoring (Screen 1)

## Tech Stack Summary
- **Next.js 14** - App Router, Server Components
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **React Query** - Data fetching & caching
- **Zustand** - State management
- **NextAuth.js** - Authentication
- **Recharts** - Charts & graphs
- **Lucide Icons** - Icon library

## Project Highlights

### ✅ Production-Ready Architecture
- Modular component structure
- Separation of concerns (UI, logic, data)
- Scalable folder organization
- Type-safe with TypeScript

### ✅ API Flexibility
- REST API ready with mock data
- GraphQL support prepared
- Switchable API client
- React Query for caching

### ✅ Authentication
- NextAuth.js integration
- Protected routes
- Session management
- Mock credentials for development

### ✅ State Management
- Zustand for global state
- React Query for server state
- Local component state where needed

### ✅ Responsive Design
- Mobile-friendly layouts
- Tailwind utility classes
- Custom component library

## Key Components

### Layout
- `Sidebar.tsx` - Navigation menu
- `Header.tsx` - Search & user menu
- `layout.tsx` - Dashboard wrapper

### UI Components
- `StatCard.tsx` - Metric display
- `ComplianceScoreCard.tsx` - Score widget
- `ComplianceFrameworkCard.tsx` - Framework status

### Charts
- `ComplianceTrendsChart.tsx` - Line chart
- `ModelRiskChart.tsx` - Area chart

### Data Tables
- `ComplianceIssuesTable.tsx` - Issues grid

## Data Flow

```
Component
    ↓
useQuery Hook (React Query)
    ↓
Mock Service
    ↓
Mock Data Constants
```

Future:
```
Component
    ↓
useQuery Hook
    ↓
API Service
    ↓
API Client (REST/GraphQL)
    ↓
Backend API
```

## Environment Variables

Already configured in `.env.local`:
```
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here-change-in-production
```

## Next Steps

1. **Run the app**: `npm run dev`
2. **Login** with demo credentials
3. **Explore** overview and compliance pages
4. **Customize** mock data in `/src/constants/mockData.ts`
5. **Add** real API endpoints when ready

## File Structure Overview

```
src/
├── app/              # Next.js pages & routes
├── components/       # React components
├── hooks/            # Custom hooks
├── lib/              # Utilities & API client
├── services/         # API services
├── store/            # State management
├── types/            # TypeScript types
└── constants/        # Mock data & constants
```

## Common Tasks

### Add New Page
1. Create folder in `app/(dashboard)/`
2. Add `page.tsx` file
3. Update sidebar navigation

### Add New API Hook
1. Add function in `/services/mock/`
2. Create hook in `/hooks/useQueries.ts`
3. Use in component

### Switch to Real API
1. Update service layer
2. Configure API base URL
3. Update API client settings

## Support

- Check `README.md` for detailed docs
- See `STRUCTURE.md` for project architecture
- All components are fully typed with TypeScript
- Mock data in `/constants/mockData.ts`
