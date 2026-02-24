import api from './api';

export interface User {
  id: string;
  email: string;
  role: string;
  organization_id: string;
  organization_name?: string;
  organizations?: Array<{
    id: string;
    name: string;
    domain?: string;
  }>;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  organization_name?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  organization?: {
    id: string;
    name: string;
    domain?: string;
    created_at: string;
  };
}

export class AuthService {
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post('/auth/login', credentials);
    const authData = response.data;

    // Store token and user data
    localStorage.setItem('auth_token', authData.access_token);
    localStorage.setItem('refresh_token', authData.refresh_token);

    // Merge organization info into user if available
    const userData = {
      ...authData.user,
      organization_name: authData.organization?.name,
      organization_id: authData.user.organization_id || authData.organization?.id,
    };

    localStorage.setItem('user_data', JSON.stringify(userData));

    return authData;
  }

  static async register(data: RegisterData): Promise<AuthResponse> {
    const response = await api.post('/auth/register', data);
    const authData = response.data;

    // Store token and user data
    localStorage.setItem('auth_token', authData.access_token);
    localStorage.setItem('refresh_token', authData.refresh_token);

    // Merge organization info into user if available
    const userData = {
      ...authData.user,
      organization_name: authData.organization?.name,
      organization_id: authData.user.organization_id || authData.organization?.id,
    };

    localStorage.setItem('user_data', JSON.stringify(userData));

    return authData;
  }

  static async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Continue with logout even if API call fails
      console.error('Logout API call failed:', error);
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_data');
    }
  }

  static async resetPassword(email: string): Promise<void> {
    await api.post('/auth/reset-password', { email });
  }

  static async getCurrentUser(): Promise<User | null> {
    try {
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      return null;
    }
  }

  static getStoredUser(): User | null {
    try {
      const userData = localStorage.getItem('user_data');
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      return null;
    }
  }

  static getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  static isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
