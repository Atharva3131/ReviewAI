import { test, expect } from '@playwright/test'

test.describe('Dashboard Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token')
      localStorage.setItem('user_data', JSON.stringify({
        id: '1',
        email: 'test@example.com',
        full_name: 'Test User',
        organization_id: 'org-1'
      }))
    })

    // Mock API responses
    await page.route('**/api/v1/auth/me', async route => {
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
    })

    await page.route('**/api/v1/dashboard/metrics**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kpis: {
            average_rating: 4.2,
            monthly_reviews: 156,
            at_risk_customers: 23,
            recovery_success_rate: 78.5
          },
          charts: {
            sentiment_over_time: [
              { date: '2023-12-01', value: 0.65 },
              { date: '2023-12-02', value: 0.72 },
              { date: '2023-12-03', value: 0.68 }
            ],
            review_volume_over_time: [
              { date: '2023-12-01', value: 45 },
              { date: '2023-12-02', value: 52 },
              { date: '2023-12-03', value: 38 }
            ]
          },
          activity_feed: [
            {
              id: '1',
              type: 'review_received',
              title: 'New review received',
              description: 'Customer John Doe left a 5-star review',
              timestamp: '2023-12-03T10:30:00Z'
            },
            {
              id: '2',
              type: 'recovery_action',
              title: 'Recovery action completed',
              description: 'Email sent to at-risk customer',
              timestamp: '2023-12-03T09:15:00Z'
            }
          ],
          alerts: [
            {
              id: '1',
              type: 'high_risk_customer',
              title: 'High-risk customer detected',
              description: 'Customer Jane Smith has high churn risk',
              priority: 'high',
              timestamp: '2023-12-03T11:00:00Z'
            }
          ]
        })
      })
    })

    await page.route('**/api/v1/dashboard/activity**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          activities: [
            {
              id: '1',
              type: 'review_received',
              title: 'New review received',
              description: 'Customer John Doe left a 5-star review',
              timestamp: '2023-12-03T10:30:00Z'
            }
          ],
          total_count: 1
        })
      })
    })
  })

  test('should display dashboard with KPIs', async ({ page }) => {
    await page.goto('/dashboard')

    // Check page title
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()

    // Check KPI cards are displayed
    await expect(page.getByText('4.2')).toBeVisible() // Average rating
    await expect(page.getByText('156')).toBeVisible() // Monthly reviews
    await expect(page.getByText('23')).toBeVisible() // At-risk customers
    await expect(page.getByText('78.5%')).toBeVisible() // Recovery success rate

    // Check KPI labels
    await expect(page.getByText(/average rating/i)).toBeVisible()
    await expect(page.getByText(/monthly reviews/i)).toBeVisible()
    await expect(page.getByText(/at-risk customers/i)).toBeVisible()
    await expect(page.getByText(/recovery success rate/i)).toBeVisible()
  })

  test('should display activity feed', async ({ page }) => {
    await page.goto('/dashboard')

    // Check activity feed section
    await expect(page.getByText(/recent activity/i)).toBeVisible()
    
    // Check activity items
    await expect(page.getByText('New review received')).toBeVisible()
    await expect(page.getByText('Customer John Doe left a 5-star review')).toBeVisible()
    await expect(page.getByText('Recovery action completed')).toBeVisible()
  })

  test('should display alerts', async ({ page }) => {
    await page.goto('/dashboard')

    // Check alerts section
    await expect(page.getByText(/alerts/i)).toBeVisible()
    
    // Check alert items
    await expect(page.getByText('High-risk customer detected')).toBeVisible()
    await expect(page.getByText('Customer Jane Smith has high churn risk')).toBeVisible()
  })

  test('should display charts', async ({ page }) => {
    await page.goto('/dashboard')

    // Check for chart containers (these would contain the actual charts)
    await expect(page.locator('[data-testid="sentiment-chart"]')).toBeVisible()
    await expect(page.locator('[data-testid="review-volume-chart"]')).toBeVisible()
  })

  test('should refresh data when refresh button is clicked', async ({ page }) => {
    await page.goto('/dashboard')

    // Wait for initial load
    await expect(page.getByText('4.2')).toBeVisible()

    // Mock updated data
    await page.route('**/api/v1/dashboard/metrics**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kpis: {
            average_rating: 4.5, // Updated value
            monthly_reviews: 160, // Updated value
            at_risk_customers: 20, // Updated value
            recovery_success_rate: 82.0 // Updated value
          },
          charts: {},
          activity_feed: [],
          alerts: []
        })
      })
    })

    // Click refresh button
    await page.getByRole('button', { name: /refresh/i }).click()

    // Check updated values
    await expect(page.getByText('4.5')).toBeVisible()
    await expect(page.getByText('160')).toBeVisible()
    await expect(page.getByText('20')).toBeVisible()
    await expect(page.getByText('82.0%')).toBeVisible()
  })

  test('should handle loading states', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/v1/dashboard/metrics**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kpis: { average_rating: 4.2, monthly_reviews: 156, at_risk_customers: 23, recovery_success_rate: 78.5 },
          charts: {},
          activity_feed: [],
          alerts: []
        })
      })
    })

    await page.goto('/dashboard')

    // Should show loading indicators
    await expect(page.getByTestId('loading-spinner')).toBeVisible()
    
    // Wait for data to load
    await expect(page.getByText('4.2')).toBeVisible()
    
    // Loading indicator should be gone
    await expect(page.getByTestId('loading-spinner')).not.toBeVisible()
  })

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/dashboard/metrics**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error'
        })
      })
    })

    await page.goto('/dashboard')

    // Should show error message
    await expect(page.getByText(/error loading dashboard/i)).toBeVisible()
    
    // Should show retry button
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
  })

  test('should navigate to different sections', async ({ page }) => {
    await page.goto('/dashboard')

    // Navigate to reviews section
    await page.getByRole('link', { name: /reviews/i }).click()
    await expect(page).toHaveURL('/dashboard/reviews')

    // Navigate to customers section
    await page.getByRole('link', { name: /customers/i }).click()
    await expect(page).toHaveURL('/dashboard/customers')

    // Navigate back to dashboard
    await page.getByRole('link', { name: /dashboard/i }).click()
    await expect(page).toHaveURL('/dashboard')
  })

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto('/dashboard')

    // Check that KPI cards stack vertically on mobile
    const kpiCards = page.locator('[data-testid="kpi-card"]')
    await expect(kpiCards.first()).toBeVisible()
    
    // Check mobile navigation
    await expect(page.getByRole('button', { name: /menu/i })).toBeVisible()
  })
})