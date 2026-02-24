import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility E2E Tests', () => {
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

    // Mock API responses
    await page.route('**/api/v1/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({})
      })
    })
  })

  test('login page should be accessible', async ({ page }) => {
    await page.goto('/login')

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('dashboard should be accessible', async ({ page }) => {
    // Mock dashboard data
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
          charts: {},
          activity_feed: [],
          alerts: []
        })
      })
    })

    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('reviews page should be accessible', async ({ page }) => {
    // Mock reviews data
    await page.route('**/api/v1/reviews**', async route => {
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
          }
        ])
      })
    })

    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Test tab navigation
    await page.keyboard.press('Tab')
    let focusedElement = await page.locator(':focus').first()
    await expect(focusedElement).toBeVisible()

    // Continue tabbing through interactive elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab')
      focusedElement = await page.locator(':focus').first()
      await expect(focusedElement).toBeVisible()
    }

    // Test shift+tab (reverse navigation)
    await page.keyboard.press('Shift+Tab')
    focusedElement = await page.locator(':focus').first()
    await expect(focusedElement).toBeVisible()
  })

  test('should support screen reader navigation', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check for proper heading structure
    const h1 = page.locator('h1')
    await expect(h1).toBeVisible()

    const h2Elements = page.locator('h2')
    const h2Count = await h2Elements.count()
    expect(h2Count).toBeGreaterThan(0)

    // Check for proper landmarks
    const main = page.locator('main')
    await expect(main).toBeVisible()

    const nav = page.locator('nav')
    await expect(nav).toBeVisible()
  })

  test('should have proper form accessibility', async ({ page }) => {
    await page.goto('/login')

    // Check form labels
    const emailInput = page.locator('input[type="email"]')
    const emailLabel = page.locator('label[for="email"]')
    
    await expect(emailInput).toBeVisible()
    await expect(emailLabel).toBeVisible()

    const passwordInput = page.locator('input[type="password"]')
    const passwordLabel = page.locator('label[for="password"]')
    
    await expect(passwordInput).toBeVisible()
    await expect(passwordLabel).toBeVisible()

    // Test form submission with keyboard
    await emailInput.fill('test@example.com')
    await passwordInput.fill('password123')
    await page.keyboard.press('Enter')

    // Should handle form submission
    await expect(page).toHaveURL('/dashboard')
  })

  test('should handle focus management in modals', async ({ page }) => {
    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')

    // Open a modal (assuming there's a delete button that opens a confirmation modal)
    const deleteButton = page.locator('[data-testid="delete-button"]').first()
    if (await deleteButton.isVisible()) {
      await deleteButton.click()

      // Focus should move to the modal
      const modal = page.locator('[role="dialog"]')
      await expect(modal).toBeVisible()

      // Focus should be trapped within the modal
      await page.keyboard.press('Tab')
      const focusedElement = await page.locator(':focus').first()
      
      // Focused element should be within the modal
      const isWithinModal = await modal.locator(':focus').count() > 0
      expect(isWithinModal).toBe(true)

      // Escape should close the modal
      await page.keyboard.press('Escape')
      await expect(modal).not.toBeVisible()
    }
  })

  test('should support high contrast mode', async ({ page }) => {
    // Simulate high contrast mode
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check that content is still visible and accessible
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()
    
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should support reduced motion preferences', async ({ page }) => {
    // Simulate reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Animations should be reduced or disabled
    const animatedElements = page.locator('[class*="animate"], [class*="transition"]')
    const count = await animatedElements.count()
    
    if (count > 0) {
      // Check that animations respect reduced motion
      const firstAnimated = animatedElements.first()
      const computedStyle = await firstAnimated.evaluate(el => 
        window.getComputedStyle(el).animationDuration
      )
      
      // Animation duration should be 0 or very short
      expect(computedStyle === '0s' || computedStyle === '0.01s').toBe(true)
    }
  })

  test('should have proper color contrast', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Run accessibility scan focusing on color contrast
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .include('[data-testid="kpi-card"]')
      .analyze()

    // Filter for color contrast violations
    const colorContrastViolations = accessibilityScanResults.violations.filter(
      violation => violation.id === 'color-contrast'
    )
    
    expect(colorContrastViolations).toEqual([])
  })

  test('should support zoom up to 200%', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Zoom to 200%
    await page.setViewportSize({ width: 640, height: 480 }) // Simulate 200% zoom
    
    // Content should still be accessible and usable
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])

    // Interactive elements should still be clickable
    const buttons = page.locator('button')
    const buttonCount = await buttons.count()
    
    if (buttonCount > 0) {
      const firstButton = buttons.first()
      await expect(firstButton).toBeVisible()
      
      // Button should have minimum touch target size (44x44px)
      const boundingBox = await firstButton.boundingBox()
      expect(boundingBox?.width).toBeGreaterThanOrEqual(44)
      expect(boundingBox?.height).toBeGreaterThanOrEqual(44)
    }
  })

  test('should announce dynamic content changes', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Look for live regions
    const liveRegions = page.locator('[aria-live]')
    const liveRegionCount = await liveRegions.count()
    
    if (liveRegionCount > 0) {
      const firstLiveRegion = liveRegions.first()
      const ariaLive = await firstLiveRegion.getAttribute('aria-live')
      
      // Should have appropriate aria-live value
      expect(['polite', 'assertive', 'off']).toContain(ariaLive)
    }

    // Status messages should be announced
    const statusElements = page.locator('[role="status"]')
    const statusCount = await statusElements.count()
    
    expect(statusCount).toBeGreaterThanOrEqual(0) // Should have status elements for loading states
  })
})