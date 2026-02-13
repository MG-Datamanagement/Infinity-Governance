export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

export interface ComplianceFramework {
  id: string;
  name: string;
  score: number;
  policiesTotal: number;
  policiesComplete: number;
  status: 'excellent' | 'warning' | 'critical';
  lastUpdated: string;
  items?: ComplianceItem[];
}

export interface ComplianceItem {
  label: string;
  completed: boolean;
  count?: number;
}

export interface ComplianceIssue {
  id: string;
  issue: string;
  framework: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  dataset: string;
  assignee: string;
  dueDate: string;
}

export interface ComplianceTrend {
  month: string;
  overall: number;
  gdpr: number;
  soc2: number;
  hipaa: number;
}

export interface DashboardStats {
  totalAssets: number;
  totalAssetsChange: string;
  governanceScore: number;
  governanceScoreStatus: string;
  classified: number;
  classifiedChange: string;
  pendingReview: number;
  aiRiskDomains: number;
}

export interface AIGovernanceSnapshot {
  modelsInProduction: number;
  flaggedPromptsToday: number;
  aiFairnessScore: number;
  modelsNeedingReview: number;
}

export interface ModelRiskTrend {
  day: string;
  risk: number;
}

export interface DomainAsset {
  domain: string;
  count: number;
}

export interface PlatformUsage {
  platform: string;
  count: number;
}

export interface RecentActivity {
  id: string;
  name: string;
  type: string;
  table: string;
  timestamp: string;
}
