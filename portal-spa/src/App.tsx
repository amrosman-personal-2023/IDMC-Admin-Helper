import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './components/LandingPage'
import LoginPage from './components/LoginPage'
import PortalHome from './components/PortalHome'
import { AdminAuthProvider } from './admin/context/AdminAuthContext'
import AdminGuard from './admin/components/AdminGuard'
import AdminLayout from './admin/components/AdminLayout'
import AdminLoginPage from './admin/components/AdminLoginPage'
import Dashboard from './admin/components/Dashboard'
import VendorManagement from './admin/components/VendorManagement'
import DeviceRegistry from './admin/components/DeviceRegistry'
import AuditLogViewer from './admin/components/AuditLogViewer'
import SessionOverview from './admin/components/SessionOverview'
import ExtensionsManager from './admin/components/ExtensionsManager'
import LogAnalyser from './admin/components/LogAnalyser'
import LlmSettingsPage from './admin/components/LlmSettingsPage'

function AdminRoutes() {
  return (
    <AdminAuthProvider>
      <Routes>
        <Route path="login" element={<AdminLoginPage />} />
        <Route element={<AdminGuard><AdminLayout /></AdminGuard>}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="vendors" element={<VendorManagement />} />
          <Route path="vendors/:id/devices" element={<DeviceRegistry />} />
          <Route path="devices" element={<DeviceRegistry />} />
          <Route path="audit" element={<AuditLogViewer />} />
          <Route path="sessions" element={<SessionOverview />} />
          <Route path="extensions" element={<ExtensionsManager />} />
          <Route path="logs" element={<LogAnalyser />} />
          <Route path="settings/llm" element={<LlmSettingsPage />} />
          <Route index element={<Navigate to="dashboard" replace />} />
        </Route>
      </Routes>
    </AdminAuthProvider>
  )
}

export default function App() {
  return (
    <Routes>
      <Route index element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/portal" element={<PortalHome />} />
      <Route path="/upload" element={<PortalHome />} />
      <Route path="/operations" element={<PortalHome />} />
      <Route path="/admin/*" element={<AdminRoutes />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
