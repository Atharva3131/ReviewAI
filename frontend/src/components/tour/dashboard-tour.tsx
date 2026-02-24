'use client';

import { TourStep } from './tour-provider';

export const DASHBOARD_TOUR_ID = 'dashboard-intro';

export const dashboardTourSteps: TourStep[] = [
  {
    id: 'welcome',
    target: '[data-tour="dashboard-title"]',
    title: 'Welcome to ReviewAI!',
    content:
      "Let's take a quick tour of your reputation management dashboard. This will only take a minute.",
    placement: 'bottom',
  },
  {
    id: 'kpi-cards',
    target: '[data-tour="kpi-cards"]',
    title: 'Key Performance Indicators',
    content:
      'These cards show your most important metrics at a glance: average rating, review count, at-risk customers, and recovery success rate.',
    placement: 'bottom',
  },
  {
    id: 'activity-feed',
    target: '[data-tour="activity-feed"]',
    title: 'Recent Activity',
    content:
      'Stay updated with real-time notifications about new reviews, recovery actions, and system responses.',
    placement: 'right',
  },
  {
    id: 'action-queue',
    target: '[data-tour="action-queue"]',
    title: 'Action Queue',
    content: 'Items that need your attention are listed here. Click on any item to take action.',
    placement: 'left',
  },
  {
    id: 'sentiment-chart',
    target: '[data-tour="sentiment-chart"]',
    title: 'Sentiment Trends',
    content:
      'Track how customer sentiment changes over time to identify patterns and measure improvement.',
    placement: 'top',
  },
  {
    id: 'navigation',
    target: '[data-tour="navigation"]',
    title: 'Navigation Menu',
    content:
      'Use this menu to access Reviews, Customers, Analytics, and Settings. Each section provides detailed tools for managing your reputation.',
    placement: 'right',
  },
  {
    id: 'help-button',
    target: '[data-tour="help-button"]',
    title: 'Need Help?',
    content:
      'Click the help button anytime to access documentation, restart this tour, or contact support.',
    placement: 'left',
  },
];
