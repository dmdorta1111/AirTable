import { createBrowserRouter } from "react-router-dom"
import MainLayout from "@/components/layout/MainLayout"
import DashboardPage from "@/routes/DashboardPage"
import AnalyticsDashboardPage from "@/pages/DashboardPage"
import DashboardBuilderPage from "@/pages/DashboardBuilderPage"
import DashboardTemplatesPage from "@/pages/DashboardTemplatesPage"
import DashboardViewPage from "@/pages/DashboardViewPage"
import SharedDashboardPage from "@/pages/SharedDashboardPage"
import ChartTestPage from "@/pages/ChartTestPage"
import GridViewChartTestPage from "@/pages/GridViewChartTestPage"
import ChartExportTestPage from "@/pages/ChartExportTestPage"
import RealtimeChartTestPage from "@/pages/RealtimeChartTestPage"
import ReportTemplatesPage from "@/pages/ReportTemplatesPage"
import ReportsListPage from "@/pages/reports/ReportsListPage"
import ReportBuilderPage from "@/pages/reports/ReportBuilderPage"
import TrashPage from "@/pages/TrashPage"
import SearchPage from "@/pages/SearchPage"
import BaseDetailPage from "@/routes/BaseDetailPage"
import TableViewPage from "@/routes/TableViewPage"
import LoginPage from "@/routes/LoginPage"
import RegisterPage from "@/routes/RegisterPage"
import ExtractionTestPage from "@/routes/ExtractionTestPage"
import SSOCallback from "@/features/auth/components/SSOCallback"
import SSOConfigPage from "@/features/admin/pages/SSOConfigPage"

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/shared/:token",
    element: <SharedDashboardPage />,
  },
  {
    path: "/auth/callback",
    element: <SSOCallback />,
  },
  {
    path: "/",
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "bases/:baseId",
        element: <BaseDetailPage />,
      },
      {
        path: "tables/:tableId",
        element: <TableViewPage />,
      },
      {
        path: "extraction-test",
        element: <ExtractionTestPage />,
      },
      {
        path: "dashboards",
        element: <AnalyticsDashboardPage />,
      },
      {
        path: "dashboards/new",
        element: <DashboardBuilderPage />,
      },
      {
        path: "dashboards/templates",
        element: <DashboardTemplatesPage />,
      },
      {
        path: "dashboards/:id",
        element: <DashboardViewPage />,
      },
      {
        path: "dashboards/test",
        element: <ChartTestPage />,
      },
      {
        path: "dashboards/gridview-test",
        element: <GridViewChartTestPage />,
      },
      {
        path: "dashboards/export-test",
        element: <ChartExportTestPage />,
      },
      {
        path: "dashboards/realtime-test",
        element: <RealtimeChartTestPage />,
      },
      {
        path: "reports",
        element: <ReportsListPage />,
      },
      {
        path: "reports/new",
        element: <ReportBuilderPage />,
      },
      {
        path: "reports/:reportId/edit",
        element: <ReportBuilderPage />,
      },
      {
        path: "reports/templates",
        element: <ReportTemplatesPage />,
      },
      {
        path: "trash",
        element: <TrashPage />,
      },
      {
        path: "search",
        element: <SearchPage />,
      },
      {
        path: "admin/sso",
        element: <SSOConfigPage />,
      },
    ],
  },
])