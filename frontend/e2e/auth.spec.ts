import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for consistent testing
    await page.route('**/api/v1/auth/login', async route => {
      if (route.request().method() === 'POST') {
        const postData = route.request().postDataJSON()
        
        if (postData.email === 'test@example.com' && postData.password === 'password123') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              access_token: 'mock-token',
              token_type: 'bearer',
              user: {
                id: '1',
                email: 'test@example.com',
                full_name: 'Test User',
                organization_id: 'org-1',
                organizations: [
                  { id: 'org-1', name: 'Test Organization' }
                ]
              }
            })
          })
        } else {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'Invalid credentials'
            })
          })
        }
      }
    })

    await page.route('**/api/v1/auth/me', async route => {
      const authHeader = route.request().headers()['authorization']
      
      if (authHeader === 'Bearer mock-token') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '1',
            email: 'test@example.com',
            full_name: 'Test User',
            organization_id: 'org-1'
          })
        })
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Invalid token'
          })
        })
      }
    })
  })

  test('should display login form', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Should show dashboard content
    await expect(page.getByText(/dashboard/i)).toBeVisible()
  })

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel(/email/i).fill('wrong@example.com')
    await page.getByLabel(/password/i).fill('wrongpassword')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should show error message
    await expect(page.getByText(/invalid credentials/i)).toBeVisible()
    
    // Should stay on login page
    await expect(page).toHaveURL('/login')
  })

  test('should validate required fields', async ({ page }) => {
    await page.goto('/login')

    // Try to submit without filling fields
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should show validation errors
    await expect(page.getByText(/email is required/i)).toBeVisible()
    await expect(page.getByText(/password is required/i)).toBeVisible()
  })

  test('should validate email format', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel(/email/i).fill('invalid-email')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should show email validation error
    await expect(page.getByText(/invalid email/i)).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL('/dashboard')

    // Then logout
    await page.getByRole('button', { name: /logout/i }).click()

    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    await page.goto('/dashboard')

    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })

  test('should redirect to dashboard when accessing login while authenticated', async ({ page }) => {
    // Mock authenticated state
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token')
      localStorage.setItem('user_data', JSON.stringify({
        id: '1',
        email: 'test@example.com',
        organization_id: 'org-1'
      }))
    })

    await page.goto('/login')

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
  })
})