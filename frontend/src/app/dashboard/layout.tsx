'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/components/auth/auth-provider';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { Button } from '@/components/ui/button';
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  Star,
  TrendingUp,
  Ticket,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { TourProvider } from '@/components/tour/tour-provider';
import { TourSpotlight } from '@/components/tour/tour-spotlight';
import { HelpMenu } from '@/components/help/help-menu';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Reviews', href: '/dashboard/reviews', icon: MessageSquare },
  { name: 'Customers', href: '/dashboard/customers', icon: Users },
  { name: 'Support', href: '/dashboard/support', icon: Ticket },
  { name: 'Analytics', href: '/dashboard/analytics', icon: TrendingUp },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <ProtectedRoute>
      <TourProvider>
        <div className='min-h-screen bg-gray-50'>
          {/* Mobile sidebar */}
          <div className={cn('fixed inset-0 z-50 lg:hidden', sidebarOpen ? 'block' : 'hidden')}>
            <div
              className='fixed inset-0 bg-gray-600 bg-opacity-75'
              onClick={() => setSidebarOpen(false)}
            />
            <div className='fixed inset-y-0 left-0 flex w-64 flex-col bg-white shadow-xl'>
              <div className='flex h-16 items-center justify-between px-4'>
                <div className='flex items-center'>
                  <Star className='h-8 w-8 text-blue-600' />
                  <span className='ml-2 text-xl font-bold text-gray-900'>ReviewAI <span className='text-sm font-normal text-gray-500'>Beta</span></span>
                </div>
                <Button variant='ghost' size='icon' onClick={() => setSidebarOpen(false)}>
                  <X className='h-6 w-6' />
                </Button>
              </div>
              <nav className='flex-1 space-y-1 px-2 py-4' data-tour='navigation'>
                {navigation.map(item => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'group flex items-center px-2 py-2 text-sm font-medium rounded-md',
                        isActive
                          ? 'bg-blue-100 text-blue-900'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                      )}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon
                        className={cn(
                          'mr-3 h-6 w-6',
                          isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500',
                        )}
                      />
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
              <div className='border-t border-gray-200 p-4'>
                <div className='flex items-center'>
                  <div className='flex-shrink-0'>
                    <div className='h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center'>
                      <span className='text-sm font-medium text-white'>
                        {user?.email?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className='ml-3'>
                    <p className='text-sm font-medium text-gray-700'>{user?.email}</p>
                    <p className='text-xs text-gray-500'>{user?.organization_name}</p>
                  </div>
                </div>
                <Button variant='ghost' className='mt-3 w-full justify-start' onClick={logout}>
                  <LogOut className='mr-2 h-4 w-4' />
                  Sign out
                </Button>
              </div>
            </div>
          </div>

          {/* Desktop sidebar */}
          <div className='hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col'>
            <div className='flex flex-col flex-grow bg-white border-r border-gray-200'>
              <div className='flex h-16 items-center px-4'>
                <Star className='h-8 w-8 text-blue-600' />
                <span className='ml-2 text-xl font-bold text-gray-900'>ReviewAI <span className='text-sm font-normal text-gray-500'>Beta</span></span>
              </div>
              <nav className='flex-1 space-y-1 px-2 py-4' data-tour='navigation'>
                {navigation.map(item => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'group flex items-center px-2 py-2 text-sm font-medium rounded-md',
                        isActive
                          ? 'bg-blue-100 text-blue-900'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                      )}
                    >
                      <item.icon
                        className={cn(
                          'mr-3 h-6 w-6',
                          isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500',
                        )}
                      />
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
              <div className='border-t border-gray-200 p-4'>
                <div className='flex items-center'>
                  <div className='flex-shrink-0'>
                    <div className='h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center'>
                      <span className='text-sm font-medium text-white'>
                        {user?.email?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className='ml-3'>
                    <p className='text-sm font-medium text-gray-700'>{user?.email}</p>
                    <p className='text-xs text-gray-500'>{user?.organization_name}</p>
                  </div>
                </div>
                <Button variant='ghost' className='mt-3 w-full justify-start' onClick={logout}>
                  <LogOut className='mr-2 h-4 w-4' />
                  Sign out
                </Button>
              </div>
            </div>
          </div>

          {/* Main content */}
          <div className='lg:pl-64'>
            {/* Top bar */}
            <div className='sticky top-0 z-40 flex h-16 bg-white shadow-sm border-b border-gray-200'>
              <Button
                variant='ghost'
                size='icon'
                className='lg:hidden'
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className='h-6 w-6' />
              </Button>
              <div className='flex flex-1 justify-between px-4 lg:px-6'>
                <div className='flex flex-1'>{/* Search could go here */}</div>
                <div className='ml-4 flex items-center gap-3 md:ml-6'>
                  <span className='text-sm text-gray-500'>{user?.organization_name}</span>
                  <HelpMenu />
                </div>
              </div>
            </div>

            {/* Page content */}
            <main className='flex-1'>
              <div className='py-6'>{children}</div>

              {/* Footer */}
              <footer className='border-t border-gray-200 bg-white mt-8'>
                <div className='px-4 py-4 text-center'>
                  <p className='text-xs text-gray-500'>
                    &copy; 2026 ReviewAI. All rights reserved.
                  </p>
                  <p className='text-xs text-gray-400 mt-1'>
                    Powered by <span className='font-semibold text-gray-500'>Axionyx Labs</span>
                  </p>
                </div>
              </footer>
            </main>
          </div>
        </div>

        {/* Tour Spotlight */}
        <TourSpotlight />
      </TourProvider>
    </ProtectedRoute>
  );
}
