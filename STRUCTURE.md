# Project Structure

```
infinity-governance/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx              # Login page
│   │   ├── (dashboard)/
│   │   │   ├── overview/
│   │   │   │   └── page.tsx              # Overview dashboard (Screen 2)
│   │   │   ├── compliance/
│   │   │   │   └── page.tsx              # Compliance page (Screen 1)
│   │   │   └── layout.tsx                # Dashboard layout wrapper
│   │   ├── api/
│   │   │   └── auth/
│   │   │       └── [...nextauth]/
│   │   │           └── route.ts          # NextAuth API route
│   │   ├── layout.tsx                    # Root layout
│   │   ├── page.tsx                      # Root redirect
│   │   ├── providers.tsx                 # React Query & NextAuth providers
│   │   └── globals.css                   # Global styles
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx               # Navigation sidebar
│   │   │   └── Header.tsx                # Page header
│   │   ├── ui/
│   │   │   ├── StatCard.tsx              # Reusable stat card
│   │   │   └── ComplianceScoreCard.tsx   # Compliance score display
│   │   ├── charts/
│   │   │   ├── ComplianceTrendsChart.tsx # Compliance trends chart
│   │   │   └── ModelRiskChart.tsx        # AI model risk chart
│   │   └── compliance/
│   │       ├── ComplianceFrameworkCard.tsx
│   │       └── ComplianceIssuesTable.tsx
│   ├── hooks/
│   │   └── useQueries.ts                 # React Query hooks
│   ├── lib/
│   │   ├── api-client.ts                 # API client (REST/GraphQL)
│   │   └── utils.ts                      # Utility functions
│   ├── services/
│   │   ├── api/                          # API service layer (future)
│   │   └── mock/
│   │       └── index.ts                  # Mock API service
│   ├── store/
│   │   └── appStore.ts                   # Zustand state management
│   ├── types/
│   │   └── index.ts                      # TypeScript type definitions
│   └── constants/
│       └── mockData.ts                   # Mock data constants
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── next.config.js
├── .env.local
├── .gitignore
├── .eslintrc.json
└── README.md

## Key Files

### Pages
- `/app/(dashboard)/compliance/page.tsx` - Compliance monitoring page
- `/app/(dashboard)/overview/page.tsx` - Overview dashboard
- `/app/(auth)/login/page.tsx` - Login page

### Components
- `/components/layout/Sidebar.tsx` - Navigation sidebar with menu items
- `/components/layout/Header.tsx` - Top header with search
- `/components/compliance/ComplianceFrameworkCard.tsx` - Framework cards
- `/components/compliance/ComplianceIssuesTable.tsx` - Issues table
- `/components/charts/ComplianceTrendsChart.tsx` - Trends visualization
- `/components/ui/StatCard.tsx` - Reusable metric cards

### Configuration
- `/lib/api-client.ts` - Switchable REST/GraphQL client
- `/hooks/useQueries.ts` - React Query data hooks
- `/store/appStore.ts` - Global state (sidebar, theme)
- `/constants/mockData.ts` - Mock data for development

## Authentication
- NextAuth.js with credentials provider
- Mock account: shivam@infinity.com / password
- Session management with JWT

## Data Flow
1. Components use React Query hooks from `/hooks/useQueries.ts`
2. Hooks call service layer from `/services/mock/`
3. Service layer returns mock data from `/constants/mockData.ts`
4. Future: Service layer will call `/lib/api-client.ts` for real API

## Styling
- Tailwind CSS utility classes
- Custom components in `/components/ui/`
- Global styles in `/app/globals.css`
- Responsive design with mobile support
```
