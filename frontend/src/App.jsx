import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './layouts/AppShell';
import { AppProvider, useApp } from './state/AppContext';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { ControlRoomPage } from './pages/ControlRoomPage';
import { FootprintPage } from './pages/FootprintPage';
import { LeaksPage } from './pages/LeaksPage';
import { SolutionsPage } from './pages/SolutionsPage';
import { DecisionStudioPage } from './pages/DecisionStudioPage';
import { WhatIfLabPage } from './pages/WhatIfLabPage';
import { CarbonTwinPage } from './pages/CarbonTwinPage';
import { ActionPlanPage } from './pages/ActionPlanPage';
import { EvidencePage } from './pages/EvidencePage';
import { CopilotPage } from './pages/CopilotPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { Toast } from './components/Toast';

function RequireAuth({ children }) {
  const { authed } = useApp();
  if (!authed) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
        <Route path="/app" element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<ControlRoomPage />} />
          <Route path="footprint" element={<FootprintPage />} />
          <Route path="leaks" element={<LeaksPage />} />
          <Route path="solutions" element={<SolutionsPage />} />
          <Route path="studio" element={<DecisionStudioPage />} />
          <Route path="what-if" element={<WhatIfLabPage />} />
          <Route path="twin" element={<CarbonTwinPage />} />
          <Route path="action-plan" element={<ActionPlanPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="copilot" element={<CopilotPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toast />
    </AppProvider>
  );
}
