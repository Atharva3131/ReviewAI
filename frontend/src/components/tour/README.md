# Feature Tour System

The feature tour system provides an interactive, step-by-step guide for users to learn about the application's features.

## Components

### TourProvider

Context provider that manages tour state across the application.

**Features:**
- Start/stop tours
- Navigate between steps
- Track completed tours in localStorage
- Persist tour completion state

**Usage:**
```tsx
import { TourProvider } from '@/components/tour/tour-provider'

function App() {
  return (
    <TourProvider>
      {/* Your app content */}
    </TourProvider>
  )
}
```

### useTour Hook

Hook to access tour functionality in components.

**API:**
```tsx
const {
  isActive,           // boolean - is tour currently active
  currentStep,        // number - current step index
  steps,              // TourStep[] - array of tour steps
  startTour,          // (steps: TourStep[]) => void
  nextStep,           // () => void
  prevStep,           // () => void
  skipTour,           // () => void
  completeTour,       // () => void
  hasCompletedTour,   // (tourId: string) => boolean
  markTourComplete,   // (tourId: string) => void
} = useTour()
```

### TourSpotlight

Visual component that highlights tour targets and displays step information.

**Features:**
- Spotlight effect on target elements
- Tooltip with step content
- Navigation controls
- Progress indicators
- Responsive positioning

### TourStep Interface

```tsx
interface TourStep {
  id: string                    // Unique step identifier
  target: string                // CSS selector for target element
  title: string                 // Step title
  content: string               // Step description
  placement?: 'top' | 'bottom' | 'left' | 'right'  // Tooltip position
  action?: () => void           // Optional action to run on step
}
```

## Creating a Tour

1. Define tour steps:

```tsx
import { TourStep } from '@/components/tour/tour-provider'

export const myTourSteps: TourStep[] = [
  {
    id: 'welcome',
    target: '[data-tour="welcome"]',
    title: 'Welcome!',
    content: 'Let\'s get started with a quick tour.',
    placement: 'bottom',
  },
  {
    id: 'feature-1',
    target: '[data-tour="feature-1"]',
    title: 'Feature 1',
    content: 'This is how you use feature 1.',
    placement: 'right',
  },
]
```

2. Add data-tour attributes to target elements:

```tsx
<div data-tour="welcome">
  Welcome content
</div>

<div data-tour="feature-1">
  Feature 1 content
</div>
```

3. Start the tour:

```tsx
import { useTour } from '@/components/tour/tour-provider'
import { myTourSteps } from './my-tour'

function MyComponent() {
  const { startTour } = useTour()
  
  const handleStartTour = () => {
    startTour(myTourSteps)
  }
  
  return (
    <button onClick={handleStartTour}>
      Start Tour
    </button>
  )
}
```

## Auto-starting Tours

To automatically start a tour for first-time users:

```tsx
import { useEffect } from 'react'
import { useTour } from '@/components/tour/tour-provider'
import { myTourSteps, MY_TOUR_ID } from './my-tour'

function MyComponent() {
  const { startTour, hasCompletedTour, markTourComplete } = useTour()
  
  useEffect(() => {
    if (!hasCompletedTour(MY_TOUR_ID)) {
      const timer = setTimeout(() => {
        startTour(myTourSteps)
        markTourComplete(MY_TOUR_ID)
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [hasCompletedTour, startTour, markTourComplete])
  
  return <div>Content</div>
}
```

## Best Practices

1. **Target Selection**: Use `data-tour` attributes for tour targets to avoid coupling with styling classes
2. **Step Count**: Keep tours concise (5-7 steps maximum)
3. **Content**: Write clear, actionable descriptions
4. **Timing**: Delay auto-start by 1-2 seconds to let the page load
5. **Persistence**: Always mark tours as complete to avoid annoying repeat users
6. **Accessibility**: Ensure tour content is keyboard navigable

## Styling

The tour uses Tailwind CSS classes and can be customized by modifying:
- `tour-spotlight.tsx` - Spotlight and tooltip styling
- Overlay opacity and colors
- Tooltip positioning and sizing
- Progress indicator appearance

## Testing

Tests are located in `__tests__/tour-provider.test.tsx` and cover:
- Tour initialization
- Step navigation
- Tour completion
- localStorage persistence
- Hook functionality
