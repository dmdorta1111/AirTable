import React from 'react';
import { SharedDashboardView } from '@/components/analytics/SharedDashboardView';

/**
 * Shared Dashboard Page
 *
 * This page renders a shared dashboard in read-only mode.
 * It does not require authentication and uses a share token from the URL.
 *
 * URL pattern: /shared/{shareToken}
 */
export const SharedDashboardPage: React.FC = () => {
  // SharedDashboardView extracts the share token from the URL params
  // and fetches the dashboard data without requiring authentication
  return <SharedDashboardView />;
};

export default SharedDashboardPage;
