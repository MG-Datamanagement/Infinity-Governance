import {
  MOCK_COMPLIANCE_FRAMEWORKS,
  MOCK_COMPLIANCE_ISSUES,
  MOCK_COMPLIANCE_TRENDS,
  MOCK_DASHBOARD_STATS,
  MOCK_AI_SNAPSHOT,
  MOCK_MODEL_RISK_TRENDS,
  MOCK_DOMAIN_ASSETS,
  MOCK_PLATFORM_USAGE,
  MOCK_RECENT_ACTIVITY,
} from '@/constants/mockData';

// Simulate API delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const mockApiService = {
  async getComplianceFrameworks() {
    await delay(300);
    return MOCK_COMPLIANCE_FRAMEWORKS;
  },

  async getComplianceIssues() {
    await delay(400);
    return MOCK_COMPLIANCE_ISSUES;
  },

  async getComplianceTrends() {
    await delay(350);
    return MOCK_COMPLIANCE_TRENDS;
  },

  async getDashboardStats() {
    await delay(250);
    return MOCK_DASHBOARD_STATS;
  },

  async getAISnapshot() {
    await delay(300);
    return MOCK_AI_SNAPSHOT;
  },

  async getModelRiskTrends() {
    await delay(350);
    return MOCK_MODEL_RISK_TRENDS;
  },

  async getDomainAssets() {
    await delay(200);
    return MOCK_DOMAIN_ASSETS;
  },

  async getPlatformUsage() {
    await delay(200);
    return MOCK_PLATFORM_USAGE;
  },

  async getRecentActivity() {
    await delay(250);
    return MOCK_RECENT_ACTIVITY;
  },
};
