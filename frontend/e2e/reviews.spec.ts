import { test, expect } from '@playwright/test'

test.describe('Reviews Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token')
      localStorage.setItem('user_data', JSON.stringify({
        id: '1',
        email: 'test@example.com',
        organization_id: 'org-1'
      }))
    })

    // Mock reviews API
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
            title: 'Great service!',
            content: 'I had an excellent experience with this company. The staff was friendly and professional.',
            rating: 5,
            sentiment_score: 0.85,
            sentiment_label: 'Positive',
            urgency_level: 'low',
            issue_categories: ['service'],
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
              title: 'Great service!',
              content: 'Excellent experience',
              rating: 5,
              sentiment_score: 0.85,
              sentiment_label: 'Positive',
              urgency_level: 'low',
              review_date: '2023-12-03T10:30:00Z'
            },
            {
              id: '2',
              platform: 'yelp',
              customer_name: 'Jane Smith',
              title: 'Poor experience',
              content: 'Service was slow and food was cold',
              rating: 2,
              sentiment_score: 0.25,
              sentiment_label: 'Negative',
              urgency_level: 'high',
              review_date: '2023-12-02T15:45:00Z'
            },
            {
              id: '3',
              platform: 'facebook',
              customer_name: 'Bob Johnson',
              title: 'Average service',
              content: 'It was okay, nothing special',
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

    // Mock review response generation
    await page.route('**/api/v1/reviews/respond', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          review_id: '1',
          response_content: 'Thank you for your wonderful review! We appreciate your feedback.',
          response_type: 'public',
          tone: 'professional',
          confidence_score: 0.92,
          requires_approval: false,
          generated_at: '2023-12-03T11:00:00Z'
        })
      })
    })
  })

  test('should display reviews list', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Check page title
    await expect(page.getByRole('heading', { name: /reviews/i })).toBeVisible()

    // Check review items are displayed
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).toBeVisible()
    await expect(page.getByText('Bob Johnson')).toBeVisible()

    // Check review content
    await expect(page.getByText('Great service!')).toBeVisible()
    await expect(page.getByText('Poor experience')).toBeVisible()
    await expect(page.getByText('Average service')).toBeVisible()
  })

  test('should display sentiment badges correctly', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Check sentiment badges
    await expect(page.getByText('Positive')).toBeVisible()
    await expect(page.getByText('Negative')).toBeVisible()
    await expect(page.getByText('Neutral')).toBeVisible()

    // Check sentiment colors (by checking CSS classes or data attributes)
    const positiveBadge = page.locator('[data-sentiment="positive"]')
    const negativeBadge = page.locator('[data-sentiment="negative"]')
    const neutralBadge = page.locator('[data-sentiment="neutral"]')

    await expect(positiveBadge).toHaveClass(/bg-green/)
    await expect(negativeBadge).toHaveClass(/bg-red/)
    await expect(neutralBadge).toHaveClass(/bg-yellow/)
  })

  test('should display urgency indicators', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Check urgency indicators
    await expect(page.getByText('Low')).toBeVisible()
    await expect(page.getByText('High')).toBeVisible()
    await expect(page.getByText('Medium')).toBeVisible()
  })

  test('should filter reviews by platform', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Open platform filter
    await page.getByRole('button', { name: /filter/i }).click()
    await page.getByLabel(/platform/i).selectOption('google')
    await page.getByRole('button', { name: /apply/i }).click()

    // Should only show Google reviews
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).not.toBeVisible()
    await expect(page.getByText('Bob Johnson')).not.toBeVisible()
  })

  test('should filter reviews by rating', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Open rating filter
    await page.getByRole('button', { name: /filter/i }).click()
    await page.getByLabel(/minimum rating/i).fill('4')
    await page.getByRole('button', { name: /apply/i }).click()

    // Should only show high-rated reviews
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).not.toBeVisible()
    await expect(page.getByText('Bob Johnson')).not.toBeVisible()
  })

  test('should sort reviews by date', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Open sort dropdown
    await page.getByRole('button', { name: /sort/i }).click()
    await page.getByText(/oldest first/i).click()

    // Check that reviews are sorted (Bob Johnson should be first as oldest)
    const firstReview = page.locator('[data-testid="review-item"]').first()
    await expect(firstReview.getByText('Bob Johnson')).toBeVisible()
  })

  test('should open review details', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Click on a review to open details
    await page.getByText('John Doe').click()

    // Should navigate to review detail page
    await expect(page).toHaveURL(/\/dashboard\/reviews\/1/)

    // Check review details are displayed
    await expect(page.getByText('Great service!')).toBeVisible()
    await expect(page.getByText('I had an excellent experience')).toBeVisible()
    await expect(page.getByText('john@example.com')).toBeVisible()
    await expect(page.getByText('Google')).toBeVisible()
  })

  test('should generate response for review', async ({ page }) => {
    await page.goto('/dashboard/reviews/1')

    // Click generate response button
    await page.getByRole('button', { name: /generate response/i }).click()

    // Select response type and tone
    await page.getByLabel(/response type/i).selectOption('public')
    await page.getByLabel(/tone/i).selectOption('professional')
    
    // Click generate
    await page.getByRole('button', { name: /generate/i }).click()

    // Should show generated response
    await expect(page.getByText('Thank you for your wonderful review!')).toBeVisible()
    
    // Should show confidence score
    await expect(page.getByText('92%')).toBeVisible()
  })

  test('should edit generated response', async ({ page }) => {
    await page.goto('/dashboard/reviews/1')

    // Generate response first
    await page.getByRole('button', { name: /generate response/i }).click()
    await page.getByRole('button', { name: /generate/i }).click()

    // Wait for response to be generated
    await expect(page.getByText('Thank you for your wonderful review!')).toBeVisible()

    // Click edit button
    await page.getByRole('button', { name: /edit/i }).click()

    // Edit the response
    const responseTextarea = page.getByRole('textbox', { name: /response/i })
    await responseTextarea.clear()
    await responseTextarea.fill('Thank you for your amazing review! We truly appreciate your feedback.')

    // Save changes
    await page.getByRole('button', { name: /save/i }).click()

    // Should show updated response
    await expect(page.getByText('Thank you for your amazing review!')).toBeVisible()
  })

  test('should handle bulk actions', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Select multiple reviews
    await page.getByRole('checkbox', { name: /select review/i }).first().check()
    await page.getByRole('checkbox', { name: /select review/i }).nth(1).check()

    // Should show bulk actions bar
    await expect(page.getByText('2 reviews selected')).toBeVisible()
    
    // Should show bulk action buttons
    await expect(page.getByRole('button', { name: /mark as processed/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /export/i })).toBeVisible()
  })

  test('should search reviews', async ({ page }) => {
    await page.goto('/dashboard/reviews')

    // Enter search term
    await page.getByPlaceholder(/search reviews/i).fill('excellent')

    // Should filter reviews based on search
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).not.toBeVisible()
    await expect(page.getByText('Bob Johnson')).not.toBeVisible()
  })

  test('should handle pagination', async ({ page }) => {
    // Mock paginated response
    await page.route('**/api/v1/reviews**', async route => {
      const url = new URL(route.request().url())
      const page_num = url.searchParams.get('page') || '1'
      
      if (page_num === '2') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: '4',
              platform: 'tripadvisor',
              customer_name: 'Alice Brown',
              title: 'Good value',
              content: 'Decent service for the price',
              rating: 4,
              sentiment_score: 0.65,
              sentiment_label: 'Positive',
              urgency_level: 'low',
              review_date: '2023-11-30T14:20:00Z'
            }
          ])
        })
      } else {
        // Return first page data (existing mock)
        await route.continue()
      }
    })

    await page.goto('/dashboard/reviews')

    // Should show pagination controls
    await expect(page.getByRole('button', { name: /next/i })).toBeVisible()
    
    // Click next page
    await page.getByRole('button', { name: /next/i }).click()

    // Should show page 2 content
    await expect(page.getByText('Alice Brown')).toBeVisible()
  })
})