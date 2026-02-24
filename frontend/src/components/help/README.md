# Help System

The help system provides users with easy access to documentation, tutorials, and support resources.

## Components

### HelpMenu

A dropdown menu component that displays help resources and quick links.

**Features:**
- Access to documentation
- Video tutorials
- API reference
- Contact support
- Restart feature tour
- Quick links to common topics
- Responsive design

**Usage:**
```tsx
import { HelpMenu } from '@/components/help/help-menu'

function Layout() {
  return (
    <div>
      <header>
        <HelpMenu />
      </header>
    </div>
  )
}
```

## Help Resources

The help menu includes the following resources:

### 1. Take the Tour
- Restarts the interactive dashboard tour
- Helps users learn the interface
- Can be accessed anytime

### 2. Documentation
- Comprehensive guides and tutorials
- Links to `/docs`
- Covers all features in detail

### 3. Video Tutorials
- Step-by-step video guides
- Visual learning resource
- Links to `/tutorials`

### 4. API Reference
- Technical documentation for developers
- API endpoints and usage
- Links to `/api-docs`

### 5. Contact Support
- Direct email to support team
- Opens default email client
- Email: support@revive-ai.com

## Quick Links

Pre-configured links to common documentation topics:
- Getting Started Guide
- Review Management
- Customer Recovery
- Analytics & Reporting
- Integrations

## Customization

### Adding New Resources

Edit `help-menu.tsx` and add to the `helpResources` array:

```tsx
const helpResources = [
  // ... existing resources
  {
    icon: YourIcon,
    title: 'New Resource',
    description: 'Description of the resource',
    action: () => window.open('/your-link', '_blank'),
  },
]
```

### Adding Quick Links

Add to the `quickLinks` array:

```tsx
const quickLinks = [
  // ... existing links
  { label: 'New Topic', href: '/docs/new-topic' },
]
```

### Changing Contact Information

Update the contact section in the component:

```tsx
<div className="flex items-center gap-2 text-sm text-gray-600">
  <Mail className="h-4 w-4" />
  <span>your-email@example.com</span>
</div>
```

## Integration with Tour System

The help menu integrates with the tour system to allow users to restart tours:

```tsx
import { useTour } from '@/components/tour/tour-provider'
import { dashboardTourSteps, DASHBOARD_TOUR_ID } from '@/components/tour/dashboard-tour'

const { startTour, markTourComplete } = useTour()

const handleStartTour = () => {
  startTour(dashboardTourSteps)
  markTourComplete(DASHBOARD_TOUR_ID)
  setIsOpen(false)
}
```

## Styling

The help menu uses:
- Tailwind CSS for styling
- Lucide React for icons
- Radix UI Card components
- Fixed positioning for the dropdown panel

### Customizing Appearance

Modify classes in `help-menu.tsx`:
- Panel size: `w-96` (width)
- Panel position: `right-4 top-20`
- Max height: `max-h-[calc(100vh-6rem)]`
- Shadow: `shadow-2xl`

## Accessibility

The help menu includes:
- Keyboard navigation support
- ARIA labels for screen readers
- Focus management
- Backdrop click to close
- ESC key support (via button)

## Testing

Tests are located in `__tests__/help-menu.test.tsx` and cover:
- Rendering help button
- Opening/closing panel
- Displaying all resources
- Quick links visibility
- Contact information display
- Backdrop and close button functionality

## Best Practices

1. **Keep Resources Updated**: Ensure all links point to valid documentation
2. **Response Time**: Update support response time expectations
3. **Icon Consistency**: Use consistent icon style from Lucide React
4. **Mobile Friendly**: Test on mobile devices for usability
5. **Loading States**: Consider adding loading states for external links
6. **Analytics**: Track which help resources are most used

## Future Enhancements

Potential improvements:
- Search functionality within help content
- Contextual help based on current page
- Inline help tooltips
- Help article previews
- Chat support integration
- Multi-language support
