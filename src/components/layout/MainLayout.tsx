'use client';

import { ReactNode, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import Logo from '@/assets/logo.png';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { 
  Bars3Icon, 
  XMarkIcon,
  HomeIcon,
  UsersIcon,
  DocumentTextIcon,
  CogIcon,
  QuestionMarkCircleIcon,
  ArrowRightOnRectangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline';

interface MainLayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Início', href: '/dashboard', icon: HomeIcon },
  { name: 'Clientes', href: '/clientes', icon: UsersIcon },
  { name: 'Relatórios', href: '/relatorios', icon: DocumentTextIcon },
  { name: 'Configurações', href: '/configuracoes', icon: CogIcon },
  { name: 'Ajuda', href: '/ajuda', icon: QuestionMarkCircleIcon },
];

export default function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <div className="h-screen flex overflow-hidden bg-white">
      {/* Mobile menu */}
      <div className={cn(
        'fixed inset-0 flex z-40 md:hidden',
        sidebarOpen ? 'block' : 'hidden'
      )}>
        <div className="fixed inset-0 bg-black bg-opacity-25" onClick={() => setSidebarOpen(false)} />
        <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white">
          <div className="absolute top-0 right-0 -mr-12 pt-2">
            <button
              type="button"
              className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-6 w-6 text-white" />
            </button>
          </div>
          <SidebarContent pathname={pathname} collapsed={false} />
        </div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className={cn(
          'flex flex-col transition-all duration-300 ease-in-out',
          sidebarCollapsed ? 'w-16' : 'w-64'
        )}>
          <SidebarContent 
            pathname={pathname} 
            collapsed={sidebarCollapsed} 
            onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        <div className="md:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-white border-b border-gray-100">
          <button
            type="button"
            className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-gray-200"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
        </div>
        <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none" style={{ backgroundColor: '#fafafa' }}>
          {children}
        </main>
      </div>
    </div>
  );
}

function SidebarContent({ 
  pathname, 
  collapsed = false, 
  onToggleCollapse 
}: { 
  pathname: string; 
  collapsed?: boolean; 
  onToggleCollapse?: () => void; 
}) {
  return (
    <div className="flex flex-col h-0 flex-1 bg-white border-r border-gray-100">
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        {/* Header with logo and collapse button */}
        <div className="flex items-center justify-between px-4 mb-8">
          <div className={cn(
            "flex items-center transition-all duration-300",
            collapsed ? "justify-center" : ""
          )}>
            <div className={cn(
          'relative rounded-lg flex items-center justify-center overflow-hidden',
          collapsed ? 'w-8 h-8' : 'w-40 h-40'
            )}>
            <Image src={Logo} alt="Orion Logo" fill className="object-contain" />
            </div>
            {!collapsed && (
              <h1 className="ml-3 text-xl font-semibold text-black"></h1>
            )}
          </div>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {collapsed ? (
                <ChevronRightIcon className="h-5 w-5" />
              ) : (
                <ChevronLeftIcon className="h-5 w-5" />
              )}
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || 
                           (item.href !== '/dashboard' && pathname.startsWith(item.href));
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-gray-50 text-black border-l-3 border-black'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-black',
                  collapsed ? 'justify-center' : ''
                )}
                title={collapsed ? item.name : undefined}
              >
                <item.icon
                  className={cn(
                    'flex-shrink-0 h-5 w-5',
                    isActive ? 'text-black' : 'text-gray-500 group-hover:text-gray-700',
                    collapsed ? '' : 'mr-3'
                  )}
                />
                {!collapsed && (
                  <span className="truncate">{item.name}</span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User section */}
      <div className="flex-shrink-0 border-t border-gray-100 p-4">
        <div className={cn(
          "flex items-center",
          collapsed ? "justify-center" : "w-full"
        )}>
          {!collapsed ? (
            <>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-black truncate">Empresa Contábil</p>
                <p className="text-xs text-gray-500 truncate">admin@empresa.com</p>
              </div>
              <button className="ml-3 flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 transition-colors">
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
              </button>
            </>
          ) : (
            <button 
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
              title="Sair"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
