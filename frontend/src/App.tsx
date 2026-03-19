import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '@/components/layout/Layout';
import { InstancesPage } from '@/pages/InstancesPage';
import { ChatPage } from '@/pages/ChatPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { TasksPage } from '@/pages/TasksPage';
import { MeetingsPage } from '@/pages/MeetingsPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { systemApi } from '@/services/api';
import { wsService } from '@/services/websocket';

function App() {
  // Health check
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: systemApi.health,
    refetchInterval: 30000,
  });

  // Connect WebSocket on mount
  useEffect(() => {
    wsService.connect();
    return () => {
      wsService.disconnect();
    };
  }, []);

  return (
    <Layout health={health}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/instances" element={<InstancesPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/meetings" element={<MeetingsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:sessionId" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
