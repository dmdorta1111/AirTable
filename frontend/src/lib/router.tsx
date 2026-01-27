import { createBrowserRouter } from "react-router-dom"
import MainLayout from "@/components/layout/MainLayout"
import DashboardPage from "@/routes/DashboardPage"
import AnalyticsDashboardPage from "@/pages/DashboardPage"
import DashboardBuilderPage from "@/pages/DashboardBuilderPage"
import DashboardTemplatesPage from "@/pages/DashboardTemplatesPage"
import DashboardViewPage from "@/pages/DashboardViewPage"
import SharedDashboardPage from "@/pages/SharedDashboardPage"
import ChartTestPage from "@/pages/ChartTestPage"
import ReportTemplatesPage from "@/pages/ReportTemplatesPage"
import ReportsListPage from "@/pages/reports/ReportsListPage"
import ReportBuilderPage from "@/pages/reports/ReportBuilderPage"
import BaseDetailPage from "@/routes/BaseDetailPage"
import TableViewPage from "@/routes/TableViewPage"
import LoginPage from "@/routes/LoginPage"
import RegisterPage from "@/routes/RegisterPage"
import ExtractionTestPage from "@/routes/ExtractionTestPage"

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
    ],
  },
])
