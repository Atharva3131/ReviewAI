/**
 * Authentication Configuration
 *
 * Toggle between demo mode (auto-login) and full authentication
 */

export const AUTH_CONFIG = {
  /**
   * DEMO_MODE: When true, bypasses login and uses demo credentials automatically
   * Set to false to enable full authentication with login/register pages
   */
  DEMO_MODE: true,

  /**
   * Demo user credentials (used when DEMO_MODE is true)
   */
  DEMO_CREDENTIALS: {
    email: 'demo@restaurant.com',
    password: 'demo123',
  },
};
