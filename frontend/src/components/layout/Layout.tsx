import { ReactNode, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Server,
  MessageSquare,
  LayoutDashboard,
  Menu,
  X,
  ChevronRight,
  ClipboardList,
  Users,
  Settings,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { HealthCheck } from '@/types';

interface LayoutProps {
  children: ReactNode;
  health?: HealthCheck;
}

const navigation = [
  { name: '仪表盘', href: '/', icon: LayoutDashboard },
  { name: '实例管理', href: '/instances', icon: Server },
  { name: '任务管理', href: '/tasks', icon: ClipboardList },
  { name: '会议讨论', href: '/meetings', icon: Users },
  { name: '聊天', href: '/chat', icon: MessageSquare },
  { name: '系统设置', href: '/settings', icon: Settings },
];

export function Layout({ children, health }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar */}
      <div className="lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="fixed top-4 left-4 z-50"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center border-b px-6">
          <h1 className="text-xl font-bold">OpenClaw 控制台</h1>
        </div>

        <nav className="space-y-1 p-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.name}
                {isActive && <ChevronRight className="ml-auto h-4 w-4" />}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 border-t p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">系统状态</span>
            <Badge
              variant={health?.status === 'healthy' ? 'default' : 'destructive'}
            >
              {health?.status || 'unknown'}
            </Badge>
          </div>
          {health?.version && (
            <p className="mt-1 text-xs text-muted-foreground">
              v{health.version}
            </p>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main
        className={`min-h-screen transition-all duration-300 ${
          sidebarOpen ? 'lg:ml-64' : ''
        }`}
      >
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
