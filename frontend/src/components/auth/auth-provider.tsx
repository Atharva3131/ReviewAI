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

const publicRoutes = ['/login', '/register', '/reset-password'];

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [needsOrganizationSelection, setNeedsOrganizationSelection] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const initAuth = async () => {
      try {
        // Check if user is stored locally
        const storedUser = AuthService.getStoredUser();
        const token = AuthService.getToken();

        if (storedUser && token) {
          // Verify token is still valid
          const currentUser = await AuthService.getCurrentUser();
          if (currentUser) {
            setUser(currentUser);

            // Check if user needs to select organization
            if (
              !currentUser.organization_id &&
              currentUser.organizations &&
              currentUser.organizations.length > 1
            ) {
              setNeedsOrganizationSelection(true);
            }
          } else {
            // Token is invalid, clear storage
            AuthService.logout();
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        AuthService.logout();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  useEffect(() => {
    if (!isLoading && !needsOrganizationSelection) {
      const isPublicRoute = publicRoutes.includes(pathname);
      const isAuthenticated = !!user;

      if (!isAuthenticated && !isPublicRoute) {
        router.push('/login');
      } else if (isAuthenticated && isPublicRoute) {
        router.push('/dashboard');
      }
    }
  }, [user, isLoading, needsOrganizationSelection, pathname, router]);

  const login = async (email: string, password: string) => {
    const authData = await AuthService.login({ email, password });
    setUser(authData.user);

    // Check if user needs to select organization
    if (
      !authData.user.organization_id &&
      authData.user.organizations &&
      authData.user.organizations.length > 1
    ) {
      setNeedsOrganizationSelection(true);
    }
  };

  const logout = async () => {
    await AuthService.logout();
    setUser(null);
    setNeedsOrganizationSelection(false);
    router.push('/login');
  };

  const selectOrganization = (organizationId: string) => {
    if (user) {
      const updatedUser = { ...user, organization_id: organizationId };
      setUser(updatedUser);
      localStorage.setItem('user_data', JSON.stringify(updatedUser));
      setNeedsOrganizationSelection(false);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAuthenticated: !!user,
    needsOrganizationSelection,
    selectOrganization,
  };

  // Show organization selector if needed
  if (needsOrganizationSelection && user) {
    return (
      <AuthContext.Provider value={value}>
        <OrganizationSelector user={user} onSelect={selectOrganization} />
      </AuthContext.Provider>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
