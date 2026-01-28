import React from 'react';
import { DashboardView } from '@/components/analytics/DashboardView';

/**
 * Dashboard View Page
 *
 * This page renders a dashboard with real-time WebSocket updates.
 * It uses the DashboardView component which handles:
 * - Dashboard data fetching
 * - WebSocket subscriptions for live updates
 * - Widget rendering and refresh
 */
export const DashboardViewPage: React.FC = () => {
  // DashboardView extracts the dashboard ID from the URL params
  // and handles all the logic internally
  return <DashboardView />;
};

export default DashboardViewPage;
