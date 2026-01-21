import { createBrowserRouter } from "react-router-dom"
import MainLayout from "@/components/layout/MainLayout"
import DashboardPage from "@/routes/DashboardPage"
import BaseDetailPage from "@/routes/BaseDetailPage"
import TableViewPage from "@/routes/TableViewPage"
import LoginPage from "@/routes/LoginPage"
import RegisterPage from "@/routes/RegisterPage"

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
    ],
  },
])
