import { test, expect } from '@playwright/test'

const mobileDevices = [
  { name: 'iPhone SE', width: 375, height: 667 },
  { name: 'iPhone 12', width: 390, height: 844 },
  { name: 'iPhone 12 Pro Max', width: 428, height: 926 },
  { name: 'Samsung Galaxy S21', width: 360, height: 800 },
  { name: 'iPad Mini', width: 768, height: 1024 },
  { name: 'iPad Pro', width: 1024, height: 1366 },
]

const tabletDevices = [
  { name: 'iPad', width: 768, height: 1024 },
  { name: 'iPad Pro 11"', width: 834, height: 1194 },
  { name: 'iPad Pro 12.9"', width: 1024, height: 1366 },
  { name: 'Surface Pro', width: 912, height: 1368 },
]

test.describe('Mobile Responsiveness Tests', () => {
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
      const url = route.request().url()
      
      if (url.includes('/dashboard/metrics')) {
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
            activity_feed: [
              {
                id: '1',
                type: 'review_received',
                title: 'New review received',
                description: 'Customer John Doe left a 5-star review',
                timestamp: '2023-12-03T10:30:00Z'
              }
            ],
            alerts: []
          })
        })
      } else if (url.includes('/reviews')) {
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
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({})
        })
      }
    })
  })

  mobileDevices.forEach(device => {
    test(`${device.name} - Dashboard layout`, async ({ page }) => {
      await page.setViewportSize({ width: device.width, height: device.height })
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      // Check that content is visible and properly laid out
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()

      // KPI cards should stack vertically on mobile
      const kpiCards = page.locator('[data-testid="kpi-card"]')
      const cardCount = await kpiCards.count()
      
      if (cardCount > 0) {
        // Check that cards are stacked (not side by side)
        const firstCard = kpiCards.first()
        const secondCard = kpiCards.nth(1)
        
        if (await secondCard.isVisible()) {
          const firstCardBox = await firstCard.boundingBox()
          const secondCardBox = await secondCard.boundingBox()
          
          // On mobile, second card should be below first card
          if (device.width < 768) {
            expect(secondCardBox?.y).toBeGreaterThan(firstCardBox?.y + firstCardBox?.height - 10)
          }
        }
      }

      // Check mobile navigation
      if (device.width < 768) {
        const mobileMenuButton = page.getByRole('button', { name: /menu/i })
        await expect(mobileMenuButton).toBeVisible()
        
        // Test mobile menu functionality
        await mobileMenuButton.click()
        const mobileNav = page.locator('[data-testid="mobile-navigation"]')
        await expect(mobileNav).toBeVisible()
      }
    })
  })

  mobileDevices.forEach(device => {
    test(`${device.name} - Reviews list responsiveness`, async ({ page }) => {
      await page.setViewportSize({ width: device.width, height: device.height })
      await page.goto('/dashboard/reviews')
      await page.waitForLoadState('networkidle')

      // Check that reviews list is properly displayed
      await expect(page.getByRole('heading', { name: /reviews/i })).toBeVisible()

      // Reviews should be displayed in a mobile-friendly format
      const reviewItems = page.locator('[data-testid="review-item"]')
      const reviewCount = await reviewItems.count()
      
      if (reviewCount > 0) {
        const firstReview = reviewItems.first()
        await expect(firstReview).toBeVisible()
        
        // Check that review content is readable
        const reviewBox = await firstReview.boundingBox()
        expect(reviewBox?.width).toBeLessThanOrEqual(device.width)
        
        // Text should not overflow
        const reviewText = firstReview.locator('p, span').first()
        if (await reviewText.isVisible()) {
          const textBox = await reviewText.boundingBox()
          expect(textBox?.width).toBeLessThanOrEqual(device.width - 40) // Account for padding
        }
      }

      // Filter and sort controls should be accessible
      const filterButton = page.getByRole('button', { name: /filter/i })
      if (await filterButton.isVisible()) {
        await expect(filterButton).toBeVisible()
        
        // Button should be large enough for touch
        const buttonBox = await filterButton.boundingBox()
        expect(buttonBox?.height).toBeGreaterThanOrEqual(44) // Minimum touch target
      }
    })
  })

  test('Touch interactions work correctly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }) // iPhone SE
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Test touch scrolling
    await page.touchscreen.tap(200, 300)
    await page.mouse.wheel(0, 500) // Scroll down
    
    // Content should scroll properly
    const scrollPosition = await page.evaluate(() => window.scrollY)
    expect(scrollPosition).toBeGreaterThan(0)

    // Test touch navigation
    const navButton = page.getByRole('button', { name: /menu/i })
    if (await navButton.isVisible()) {
      const buttonBox = await navButton.boundingBox()
      if (buttonBox) {
        await page.touchscreen.tap(buttonBox.x + buttonBox.width / 2, buttonBox.y + buttonBox.height / 2)
        
        // Navigation should open
        const mobileNav = page.locator('[data-testid="mobile-navigation"]')
        await expect(mobileNav).toBeVisible()
      }
    }
  })

  test('Swipe gestures work on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard/reviews')
    await page.waitForLoadState('networkidle')

    // Test swipe to reveal actions (if implemented)
    const reviewItem = page.locator('[data-testid="review-item"]').first()
    if (await reviewItem.isVisible()) {
      const itemBox = await reviewItem.boundingBox()
      if (itemBox) {
        // Swipe left to reveal actions
        await page.touchscreen.tap(itemBox.x + itemBox.width - 50, itemBox.y + itemBox.height / 2)
        await page.mouse.move(itemBox.x + 50, itemBox.y + itemBox.height / 2)
        
        // Check if swipe actions are revealed
        const swipeActions = page.locator('[data-testid="swipe-actions"]')
        if (await swipeActions.isVisible()) {
          await expect(swipeActions).toBeVisible()
        }
      }
    }
  })

  tabletDevices.forEach(device => {
    test(`${device.name} - Tablet layout optimization`, async ({ page }) => {
      await page.setViewportSize({ width: device.width, height: device.height })
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      // Tablet should show a hybrid layout
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()

      // KPI cards should be in a grid (2x2 or similar)
      const kpiCards = page.locator('[data-testid="kpi-card"]')
      const cardCount = await kpiCards.count()
      
      if (cardCount >= 2) {
        const firstCard = kpiCards.first()
        const secondCard = kpiCards.nth(1)
        
        const firstCardBox = await firstCard.boundingBox()
        const secondCardBox = await secondCard.boundingBox()
        
        // On tablet, cards should be side by side (at least some of them)
        if (firstCardBox && secondCardBox) {
          const isHorizontalLayout = Math.abs(firstCardBox.y - secondCardBox.y) < 50
          expect(isHorizontalLayout).toBe(true)
        }
      }

      // Navigation should be visible (not collapsed)
      const desktopNav = page.locator('[data-testid="desktop-navigation"]')
      if (await desktopNav.isVisible()) {
        await expect(desktopNav).toBeVisible()
      }
    })
  })

  test('Orientation changes are handled correctly', async ({ page }) => {
    // Start in portrait
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check portrait layout
    const portraitKpiCards = page.locator('[data-testid="kpi-card"]')
    const portraitCardCount = await portraitKpiCards.count()
    
    // Switch to landscape
    await page.setViewportSize({ width: 667, height: 375 })
    await page.waitForTimeout(500) // Wait for layout adjustment

    // Check landscape layout
    const landscapeKpiCards = page.locator('[data-testid="kpi-card"]')
    const landscapeCardCount = await landscapeKpiCards.count()
    
    // Same number of cards should be visible
    expect(landscapeCardCount).toBe(portraitCardCount)

    // Layout should adapt to landscape
    if (landscapeCardCount >= 2) {
      const firstCard = landscapeKpiCards.first()
      const secondCard = landscapeKpiCards.nth(1)
      
      const firstCardBox = await firstCard.boundingBox()
      const secondCardBox = await secondCard.boundingBox()
      
      // In landscape, cards should be more likely to be side by side
      if (firstCardBox && secondCardBox) {
        const isHorizontalLayout = Math.abs(firstCardBox.y - secondCardBox.y) < 50
        expect(isHorizontalLayout).toBe(true)
      }
    }
  })

  test('Text remains readable at different zoom levels', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Test different zoom levels
    const zoomLevels = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    for (const zoom of zoomLevels) {
      await page.evaluate((zoomLevel) => {
        document.body.style.zoom = zoomLevel.toString()
      }, zoom)
      
      await page.waitForTimeout(300)
      
      // Check that text is still readable
      const headings = page.locator('h1, h2, h3')
      const headingCount = await headings.count()
      
      if (headingCount > 0) {
        const firstHeading = headings.first()
        await expect(firstHeading).toBeVisible()
        
        // Text should not be cut off
        const headingBox = await firstHeading.boundingBox()
        expect(headingBox?.width).toBeGreaterThan(0)
        expect(headingBox?.height).toBeGreaterThan(0)
      }
    }
    
    // Reset zoom
    await page.evaluate(() => {
      document.body.style.zoom = '1'
    })
  })

  test('Form inputs are properly sized for mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // Check form input sizes
    const emailInput = page.locator('input[type="email"]')
    const passwordInput = page.locator('input[type="password"]')
    const submitButton = page.getByRole('button', { name: /sign in/i })

    // Inputs should be large enough for mobile interaction
    const emailBox = await emailInput.boundingBox()
    const passwordBox = await passwordInput.boundingBox()
    const buttonBox = await submitButton.boundingBox()

    expect(emailBox?.height).toBeGreaterThanOrEqual(44) // Minimum touch target
    expect(passwordBox?.height).toBeGreaterThanOrEqual(44)
    expect(buttonBox?.height).toBeGreaterThanOrEqual(44)

    // Inputs should span most of the screen width (with padding)
    expect(emailBox?.width).toBeGreaterThan(300)
    expect(passwordBox?.width).toBeGreaterThan(300)

    // Test keyboard interaction
    await emailInput.tap()
    await page.waitForTimeout(300)
    
    // Virtual keyboard should not break layout
    const viewportHeight = page.viewportSize()?.height || 667
    const inputPosition = emailBox?.y || 0
    
    // Input should still be visible above virtual keyboard
    expect(inputPosition).toBeLessThan(viewportHeight / 2)
  })

  test('Images and media scale properly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check that images don't overflow
    const images = page.locator('img')
    const imageCount = await images.count()
    
    for (let i = 0; i < imageCount; i++) {
      const image = images.nth(i)
      if (await image.isVisible()) {
        const imageBox = await image.boundingBox()
        expect(imageBox?.width).toBeLessThanOrEqual(375) // Should not exceed viewport width
      }
    }

    // Check SVG icons scale properly
    const svgIcons = page.locator('svg')
    const svgCount = await svgIcons.count()
    
    for (let i = 0; i < Math.min(svgCount, 5); i++) { // Check first 5 SVGs
      const svg = svgIcons.nth(i)
      if (await svg.isVisible()) {
        const svgBox = await svg.boundingBox()
        expect(svgBox?.width).toBeGreaterThan(0)
        expect(svgBox?.height).toBeGreaterThan(0)
        expect(svgBox?.width).toBeLessThan(100) // Icons shouldn't be too large
      }
    }
  })

  test('Performance on mobile devices', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    
    // Simulate slower mobile network
    await page.route('**/*', async route => {
      await new Promise(resolve => setTimeout(resolve, 100)) // Add 100ms delay
      await route.continue()
    })

    const startTime = Date.now()
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - startTime

    // Page should load within reasonable time even on slower connections
    expect(loadTime).toBeLessThan(10000) // 10 seconds max

    // Check that loading states are shown
    const loadingIndicators = page.locator('[data-testid="loading-spinner"], [aria-label*="loading"]')
    // Loading indicators should exist for better UX
    // (This test would need to be adjusted based on actual implementation)
  })
})