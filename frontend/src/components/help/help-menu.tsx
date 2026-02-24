'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  HelpCircle,
  BookOpen,
  Video,
  MessageCircle,
  FileText,
  PlayCircle,
  X,
  ExternalLink,
  Mail,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTour } from '@/components/tour/tour-provider';
import { dashboardTourSteps, DASHBOARD_TOUR_ID } from '@/components/tour/dashboard-tour';

interface HelpMenuProps {
  className?: string;
}

export function HelpMenu({ className }: HelpMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { startTour, markTourComplete } = useTour();

  const handleStartTour = () => {
    startTour(dashboardTourSteps);
    markTourComplete(DASHBOARD_TOUR_ID);
    setIsOpen(false);
  };

  const helpResources = [
    {
      icon: PlayCircle,
      title: 'Take the Tour',
      description: 'Interactive walkthrough of the dashboard',
      action: handleStartTour,
    },
    {
      icon: BookOpen,
      title: 'Documentation',
      description: 'Comprehensive guides and tutorials',
      action: () => window.open('/docs', '_blank'),
    },
    {
      icon: Video,
      title: 'Video Tutorials',
      description: 'Watch step-by-step video guides',
      action: () => window.open('/tutorials', '_blank'),
    },
    {
      icon: FileText,
      title: 'API Reference',
      description: 'Technical documentation for developers',
      action: () => window.open('/api-docs', '_blank'),
    },
    {
      icon: MessageCircle,
      title: 'Contact Support',
      description: 'Get help from our support team',
      action: () => window.open('mailto:support@revive-ai.com'),
    },
  ];

  const quickLinks = [
    { label: 'Getting Started Guide', href: '/docs/getting-started' },
    { label: 'Review Management', href: '/docs/reviews' },
    { label: 'Customer Recovery', href: '/docs/recovery' },
    { label: 'Analytics & Reporting', href: '/docs/analytics' },
    { label: 'Integrations', href: '/docs/integrations' },
  ];

  return (
    <div className={cn('relative', className)}>
      <Button
        variant='outline'
        size='icon'
        onClick={() => setIsOpen(!isOpen)}
        data-tour='help-button'
        className='relative'
      >
        <HelpCircle className='h-5 w-5' />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className='fixed inset-0 z-40' onClick={() => setIsOpen(false)} />

          {/* Help Panel */}
          <div className='fixed right-4 top-20 z-50 w-96 max-h-[calc(100vh-6rem)] overflow-y-auto'>
            <Card className='shadow-2xl'>
              <CardHeader className='pb-3'>
                <div className='flex items-start justify-between'>
                  <div>
                    <CardTitle className='text-xl'>Help & Resources</CardTitle>
                    <CardDescription>Find answers and learn how to use ReviewAI</CardDescription>
                  </div>
                  <Button
                    variant='ghost'
                    size='icon'
                    className='h-8 w-8 -mt-1 -mr-1'
                    onClick={() => setIsOpen(false)}
                  >
                    <X className='h-4 w-4' />
                  </Button>
                </div>
              </CardHeader>

              <CardContent className='space-y-6'>
                {/* Main Help Resources */}
                <div className='space-y-2'>
                  {helpResources.map((resource, index) => (
                    <button
                      key={index}
                      onClick={resource.action}
                      className='w-full flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors text-left'
                    >
                      <div className='flex-shrink-0 mt-0.5'>
                        <resource.icon className='h-5 w-5 text-blue-600' />
                      </div>
                      <div className='flex-1 min-w-0'>
                        <div className='font-medium text-sm text-gray-900'>{resource.title}</div>
                        <div className='text-xs text-gray-500 mt-0.5'>{resource.description}</div>
                      </div>
                      <ExternalLink className='h-4 w-4 text-gray-400 flex-shrink-0 mt-1' />
                    </button>
                  ))}
                </div>

                {/* Quick Links */}
                <div>
                  <h3 className='text-sm font-semibold text-gray-900 mb-2'>Quick Links</h3>
                  <div className='space-y-1'>
                    {quickLinks.map((link, index) => (
                      <a
                        key={index}
                        href={link.href}
                        target='_blank'
                        rel='noopener noreferrer'
                        className='block text-sm text-blue-600 hover:text-blue-800 hover:underline py-1'
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                </div>

                {/* Contact Info */}
                <div className='pt-4 border-t border-gray-200'>
                  <div className='flex items-center gap-2 text-sm text-gray-600'>
                    <Mail className='h-4 w-4' />
                    <span>support@revive-ai.com</span>
                  </div>
                  <p className='text-xs text-gray-500 mt-2'>
                    Our support team typically responds within 24 hours
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
