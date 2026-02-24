import { test, expect } from '@playwright/test'
import { percySnapshot } from '@percy/playwright'

test.describe('Visual Regression Tests', () => {
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

    // Mock consistent API responses for visual testing
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
              { date: '2023-12-03', value: 0.68 },
              { date: '2023-12-04', value: 0.75 },
              { date: '2023-12-05', value: 0.70 }
            ],
            review_volume_over_time: [
              { date: '2023-12-01', value: 45 },
              { date: '2023-12-02', value: 52 },
              { date: '2023-12-03', value: 38 },
              { date: '2023-12-04', value: 61 },
              { date: '2023-12-05', value: 47 }
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
              description: 'Email sent to at-risk customer Jane Smith',
              timestamp: '2023-12-03T09:15:00Z'
            },
            {
              id: '3',
              type: 'agent_decision',
              title: 'Agent decision made',
              description: 'Automated response generated for negative review',
              timestamp: '2023-12-03T08:45:00Z'
            }
          ],
          alerts: [
            {
              id: '1',
              type: 'high_risk_customer',
              title: 'High-risk customer detected',
              description: 'Customer Alice Brown has high churn risk (85%)',
              priority: 'high',
              timestamp: '2023-12-03T11:00:00Z'
            },
            {
              id: '2',
              type: 'negative_review_spike',
              title: 'Negative review spike',
              description: '3 negative reviews received in the last hour',
              priority: 'medium',
              timestamp: '2023-12-03T10:45:00Z'
            }
          ]
        })
      })
    })

    await page.route('**/api/v1/reviews**', async route => {
      const url = route.request().url()
      
      if (url.includes('/reviews/') && !url.includes('?')) {
        // Single review endpoint
        const reviewId = url.split('/').pop()
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: reviewId,
            platform: 'google',
            customer_name: 'John Doe',
            customer_email: 'john@example.com',
            title: 'Excellent service and great food!',
            content: 'I had an amazing experience at this restaurant. The staff was incredibly friendly and attentive, and the food was absolutely delicious. The atmosphere was perfect for a date night. I will definitely be coming back and recommending this place to all my friends and family.',
            rating: 5,
            sentiment_score: 0.92,
            sentiment_label: 'Very Positive',
            urgency_level: 'low',
            issue_categories: ['service', 'food_quality'],
            processed: true,
            review_date: '2023-12-03T10:30:00Z',
            created_at: '2023-12-03T10:30:00Z'
          })
        })
      } else {
        // Reviews list endpoint
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: '1',
              platform: 'google',
              customer_name: 'John Doe',
              title: 'Excellent service and great food!',
              content: 'Amazing experience, will definitely come back!',
              rating: 5,
              sentiment_score: 0.92,
              sentiment_label: 'Very Positive',
              urgency_level: 'low',
              review_date: '2023-12-03T10:30:00Z'
            },
            {
              id: '2',
              platform: 'yelp',
              customer_name: 'Jane Smith',
              title: 'Disappointing experience',
              content: 'Service was slow and food was cold when it arrived.',
              rating: 2,
              sentiment_score: 0.15,
              sentiment_label: 'Very Negative',
              urgency_level: 'high',
              review_date: '2023-12-02T15:45:00Z'
            },
            {
              id: '3',
              platform: 'facebook',
              customer_name: 'Bob Johnson',
              title: 'Average meal, nothing special',
              content: 'It was okay, but nothing to write home about.',
              rating: 3,
              sentiment_score: 0.55,
              sentiment_label: 'Neutral',
              urgency_level: 'medium',
              review_date: '2023-12-01T09:20:00Z'
            }
          ])
        })
      }
    })

    await page.route('**/api/v1/customers**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          customers: [
            {
              id: '1',
              name: 'Alice Brown',
              email: 'alice@example.com',
              phone: '+1234567890',
              churn_risk_score: 0.85,
              bad_review_likelihood: 0.72,
              risk_level: 'high',
              total_reviews: 8,
              average_rating: 2.3,
              last_interaction: '2023-12-01T14:30:00Z'
            },
            {
              id: '2',
              name: 'Charlie Davis',
              email: 'charlie@example.com',
              phone: '+1234567891',
              churn_risk_score: 0.45,
              bad_review_likelihood: 0.38,
              risk_level: 'medium',
              total_reviews: 12,
              average_rating: 3.8,
              last_interaction: '2023-12-02T09:15:00Z'
            },
            {
              id: '3',
              name: 'Diana Wilson',
              email: 'diana@example.com',
              phone: '+1234567892',
              churn_risk_score: 0.22,
              bad_review_likelihood: 0.18,
              risk_level: 'low',
              total_reviews: 15,
              average_rating: 4.6,
              last_interaction: '2023-12-03T11:45:00Z'
            }
          ],
          total: 3
        })
      })
    })
  })

  test('Login page visual regression', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    
    // Wait for any animations to complete
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Login Page')
  })

  test('Dashboard visual regression', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Wait for all components to load
    await page.waitForSelector('[data-testid="kpi-card"]')
    await page.waitForTimeout(1000)
    
    await percySnapshot(page, 'Dashboard - Main View')
  })

  test('Dashboard with loading states', async ({ page }) => {
    // Mock slow API response to capture loading state
    await page.route('**/api/v1/dashboard/metrics**', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000))
      await route.continue()
    })

    await page.goto('/dashboard')
    
    // Capture loading state
    await percySnapshot(page, 'Dashboard - Loading State')
  })

  test('Reviews list visual regression', async ({ page }) => {
    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Reviews - List View')
  })

  test('Review detail visual regression', async ({ page }) => {
    await page.goto('/dashboard/reviews/1')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Reviews - Detail View')
  })

  test('Customers list visual regression', async ({ page }) => {
    await page.goto('/dashboard/customers')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Customers - List View')
  })

  test('Empty states visual regression', async ({ page }) => {
    // Mock empty responses
    await page.route('**/api/v1/reviews**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      })
    })

    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Reviews - Empty State')
  })

  test('Error states visual regression', async ({ page }) => {
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
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Dashboard - Error State')
  })

  test('Modal dialogs visual regression', async ({ page }) => {
    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')
    
    // Open a modal (if delete button exists)
    const deleteButton = page.locator('[data-testid="delete-button"]').first()
    if (await deleteButton.isVisible()) {
      await deleteButton.click()
      await page.waitForTimeout(300) // Wait for modal animation
      
      await percySnapshot(page, 'Modal - Confirmation Dialog')
    }
  })

  test('Form validation visual regression', async ({ page }) => {
    await page.goto('/login')
    
    // Trigger validation errors
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.waitForTimeout(300)
    
    await percySnapshot(page, 'Login - Validation Errors')
  })

  test('Mobile responsive visual regression', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Dashboard - Mobile View')
    
    // Test mobile navigation
    const menuButton = page.getByRole('button', { name: /menu/i })
    if (await menuButton.isVisible()) {
      await menuButton.click()
      await page.waitForTimeout(300)
      
      await percySnapshot(page, 'Dashboard - Mobile Navigation Open')
    }
  })

  test('Tablet responsive visual regression', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Dashboard - Tablet View')
  })

  test('Dark mode visual regression', async ({ page }) => {
    // Enable dark mode (if supported)
    await page.emulateMedia({ colorScheme: 'dark' })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Dashboard - Dark Mode')
  })

  test('High contrast mode visual regression', async ({ page }) => {
    // Simulate high contrast mode
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
    
    // Add high contrast styles
    await page.addStyleTag({
      content: `
        * {
          filter: contrast(150%) !important;
        }
      `
    })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    
    await percySnapshot(page, 'Dashboard - High Contrast Mode')
  })

  test('Component states visual regression', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Test hover states (if interactive elements exist)
    const firstButton = page.locator('button').first()
    if (await firstButton.isVisible()) {
      await firstButton.hover()
      await page.waitForTimeout(200)
      
      await percySnapshot(page, 'Components - Hover State')
    }
    
    // Test focus states
    await firstButton.focus()
    await page.waitForTimeout(200)
    
    await percySnapshot(page, 'Components - Focus State')
  })

  test('Data visualization visual regression', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Wait for charts to render
    await page.waitForSelector('[data-testid="sentiment-chart"]', { timeout: 5000 })
    await page.waitForTimeout(1000) // Extra time for chart animations
    
    await percySnapshot(page, 'Dashboard - Charts and Visualizations')
  })
})