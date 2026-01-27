import React, { useState, useEffect } from "react"
import {
  FileText,
  Download,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Search,
  Shield,
  AlertCircle,
  CheckCircle2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  listAuditLogs,
  exportAuditLogs,
  verifyAuditLogIntegrity,
} from "@/features/audit/api/auditApi"
import type { AuditLog, AuditLogQuery, AuditAction, AuditExportFormat } from "@/types"

interface AuditLogViewerProps {
  tableId?: string
  resourceId?: string
  resourceType?: string
}

const ACTION_LABELS: Record<AuditAction, string> = {
  "record.create": "Record Created",
  "record.update": "Record Updated",
  "record.delete": "Record Deleted",
  "record.bulk_create": "Records Bulk Created",
  "record.bulk_update": "Records Bulk Updated",
  "record.bulk_delete": "Records Bulk Deleted",
  "table.create": "Table Created",
  "table.update": "Table Updated",
  "table.delete": "Table Deleted",
  "field.create": "Field Created",
  "field.update": "Field Updated",
  "field.delete": "Field Deleted",
  "view.create": "View Created",
  "view.update": "View Updated",
  "view.delete": "View Deleted",
  "user.login": "User Login",
  "user.logout": "User Logout",
  "user.login_failed": "Login Failed",
  "user.password_reset": "Password Reset",
  "user.password_changed": "Password Changed",
  "workspace.create": "Workspace Created",
  "workspace.update": "Workspace Updated",
  "workspace.delete": "Workspace Deleted",
  "workspace.member_add": "Member Added",
  "workspace.member_remove": "Member Removed",
  "workspace.member_update": "Member Updated",
  "api_key.create": "API Key Created",
  "api_key.delete": "API Key Deleted",
  "api_key.use": "API Key Used",
  "automation.create": "Automation Created",
  "automation.update": "Automation Updated",
  "automation.delete": "Automation Deleted",
  "automation.run": "Automation Ran",
  "automation.run_failed": "Automation Failed",
  "export.create": "Export Created",
  "export.download": "Export Downloaded",
  "system.settings_update": "Settings Updated",
  "audit.export": "Audit Logs Exported",
  "audit.query": "Audit Logs Queried",
}

const FORMAT_DATE = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

const FORMAT_JSON = (jsonString: string | null): string => {
  if (!jsonString) return "-"
  try {
    const parsed = JSON.parse(jsonString)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return jsonString
  }
}

export const AuditLogViewer: React.FC<AuditLogViewerProps> = ({
  tableId,
  resourceId,
  resourceType,
}) => {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [page, setPage] = useState(0)
  const [pageSize] = useState(50)

  // Filter states
  const [actionFilter, setActionFilter] = useState<string>("all")
  const [userEmailFilter, setUserEmailFilter] = useState<string>("")
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>("all")
  const [startDate, setStartDate] = useState<string>("")
  const [endDate, setEndDate] = useState<string>("")

  // Integrity verification states
  const [verifyingId, setVerifyingId] = useState<string | null>(null)
  const [integrityStatus, setIntegrityStatus] = useState<Record<string, { valid: boolean; message: string }>>({})

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const query: AuditLogQuery = {
        limit: pageSize,
        offset: page * pageSize,
      }

      if (tableId) query.table_id = tableId
      if (resourceId) query.resource_id = resourceId
      if (resourceType) query.resource_type = resourceType
      if (actionFilter && actionFilter !== "all") query.action = actionFilter as AuditAction
      if (userEmailFilter) query.user_email = userEmailFilter
      if (resourceTypeFilter && resourceTypeFilter !== "all") query.resource_type = resourceTypeFilter
      if (startDate) query.start_date = new Date(startDate).toISOString()
      if (endDate) query.end_date = new Date(endDate).toISOString()

      const response = await listAuditLogs(query)
      setLogs(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error("Failed to fetch audit logs:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: AuditExportFormat) => {
    setExporting(true)
    try {
      const query: Omit<AuditLogQuery, "limit" | "offset"> = {}

      if (tableId) query.table_id = tableId
      if (resourceId) query.resource_id = resourceId
      if (resourceType) query.resource_type = resourceType
      if (actionFilter && actionFilter !== "all") query.action = actionFilter as AuditAction
      if (userEmailFilter) query.user_email = userEmailFilter
      if (resourceTypeFilter && resourceTypeFilter !== "all") query.resource_type = resourceTypeFilter
      if (startDate) query.start_date = new Date(startDate).toISOString()
      if (endDate) query.end_date = new Date(endDate).toISOString()

      const blob = await exportAuditLogs(format, query)

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().split("T")[0]}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("Failed to export audit logs:", error)
    } finally {
      setExporting(false)
    }
  }

  const handleVerifyIntegrity = async (logId: string) => {
    setVerifyingId(logId)
    try {
      const result = await verifyAuditLogIntegrity(logId)
      setIntegrityStatus((prev) => ({
        ...prev,
        [logId]: result,
      }))
    } catch (error) {
      console.error("Failed to verify integrity:", error)
      setIntegrityStatus((prev) => ({
        ...prev,
        [logId]: { valid: false, message: "Verification failed" },
      }))
    } finally {
      setVerifyingId(null)
    }
  }

  const handleResetFilters = () => {
    setActionFilter("all")
    setUserEmailFilter("")
    setResourceTypeFilter("all")
    setStartDate("")
    setEndDate("")
    setPage(0)
  }

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize])

  const handleSearch = () => {
    setPage(0)
    fetchLogs()
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Audit Logs
              </CardTitle>
              <CardDescription>
                Tamper-evident audit trail for compliance with SOC2, ISO27001, and ITAR
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport("csv")}
                disabled={exporting || logs.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport("json")}
                disabled={exporting || logs.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
              <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-4 border rounded-lg bg-muted/50">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-2 flex-1">
                <Input
                  placeholder="User email"
                  value={userEmailFilter}
                  onChange={(e) => setUserEmailFilter(e.target.value)}
                  className="h-9"
                />
                <Select value={actionFilter} onValueChange={setActionFilter}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Action" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Actions</SelectItem>
                    {Object.entries(ACTION_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="h-9"
                />
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="h-9"
                />
                <Button onClick={handleSearch} className="h-9">
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
                <Button variant="outline" onClick={handleResetFilters} className="h-9">
                  Reset
                </Button>
              </div>
            </div>

            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[180px]">Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Details</TableHead>
                    <TableHead className="w-[100px]">Integrity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8">
                        <div className="flex items-center justify-center">
                          <RefreshCw className="h-6 w-6 animate-spin mr-2" />
                          Loading audit logs...
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : logs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8">
                        <div className="flex flex-col items-center text-muted-foreground">
                          <FileText className="h-12 w-12 mb-2" />
                          <p>No audit logs found</p>
                          <p className="text-sm">Try adjusting your filters or create some activity</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-mono text-xs">
                          {FORMAT_DATE(log.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{ACTION_LABELS[log.action] || log.action}</span>
                            {log.resource_type && (
                              <span className="text-xs text-muted-foreground">{log.resource_type}</span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm">{log.user_email || "System"}</span>
                            {log.ip_address && (
                              <span className="text-xs text-muted-foreground">{log.ip_address}</span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            {log.resource_id && (
                              <span className="font-mono text-xs">{log.resource_id}</span>
                            )}
                            {log.table_id && (
                              <span className="text-xs text-muted-foreground">Table: {log.table_id}</span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1 max-w-md">
                            {log.old_value && (
                              <details className="text-xs">
                                <summary className="cursor-pointer text-destructive hover:underline">
                                  Old Value
                                </summary>
                                <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto">
                                  {FORMAT_JSON(log.old_value)}
                                </pre>
                              </details>
                            )}
                            {log.new_value && (
                              <details className="text-xs">
                                <summary className="cursor-pointer text-primary hover:underline">
                                  New Value
                                </summary>
                                <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto">
                                  {FORMAT_JSON(log.new_value)}
                                </pre>
                              </details>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleVerifyIntegrity(log.id)}
                            disabled={verifyingId === log.id}
                          >
                            {verifyingId === log.id ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : integrityStatus[log.id] ? (
                              integrityStatus[log.id].valid ? (
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                              ) : (
                                <AlertCircle className="h-4 w-4 text-destructive" />
                              )
                            ) : (
                              <Shield className="h-4 w-4 text-muted-foreground" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} of {total} logs
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Previous
                  </Button>
                  <span className="text-sm">
                    Page {page + 1} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    Next
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AuditLogViewer
