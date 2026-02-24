import axios from 'axios';

// Always use direct backend URL, bypass Next.js proxy
const API_BASE_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // Don't send cookies
});

// Request interceptor to add auth token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log the request for debugging
    console.log('[API Request]', config.method?.toUpperCase(), config.url, {
      headers: config.headers,
      data: config.data,
    });

    return config;
  },
  error => {
    return Promise.reject(error);
  },
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  response => {
    // Log successful responses
    console.log('[API Response]', response.status, response.config.url, response.data);
    return response;
  },
  error => {
    // Log error responses
    console.error('[API Error]', {
      status: error.response?.status,
      url: error.config?.url,
      data: error.response?.data,
      headers: error.response?.headers,
    });

    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_data');

      // Only redirect if not already on login page
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default api;
