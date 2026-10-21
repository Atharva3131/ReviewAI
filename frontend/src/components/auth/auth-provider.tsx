'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { AuthService, type User } from '@/lib/auth';
import { OrganizationSelector } from './organization-selector';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  needsOrganizationSelection: boolean;
  selectOrganization: (organizationId: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: React.ReactNode;
}

// DEMO MODE: single-user portfolio demo — no authentication required
const DEMO_USER: User = {
  id: 'demo-user',
  email: 'demo@reviewai.demo',
  organization_id: 'demo-org',
  organization_name: 'Demo Organisation',
  role: 'admin',
};

export function AuthProvider({ children }: AuthProviderProps) {
  // Always authenticated in demo mode — no login/JWT required
  const [user] = useState<User | null>(DEMO_USER);
  const [isLoading] = useState(false);
  const [needsOrganizationSelection] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const login = async (_email: string, _password: string) => {
    // No-op in demo mode
  };

  const logout = async () => {
    // No-op in demo mode — redirect to dashboard
    router.push('/dashboard');
  };

  const selectOrganization = (_organizationId: string) => {
    // No-op in demo mode
  };

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAuthenticated: true, // always authenticated in demo mode
    needsOrganizationSelection,
    selectOrganization,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
