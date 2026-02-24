'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface TourStep {
  id: string;
  target: string;
  title: string;
  content: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  action?: () => void;
}

interface TourContextType {
  isActive: boolean;
  currentStep: number;
  steps: TourStep[];
  startTour: (tourSteps: TourStep[]) => void;
  nextStep: () => void;
  prevStep: () => void;
  skipTour: () => void;
  completeTour: () => void;
  hasCompletedTour: (tourId: string) => boolean;
  markTourComplete: (tourId: string) => void;
}

const TourContext = createContext<TourContextType | undefined>(undefined);

const TOUR_STORAGE_KEY = 'revive-ai-completed-tours';

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<TourStep[]>([]);
  const [completedTours, setCompletedTours] = useState<Set<string>>(new Set());

  // Load completed tours from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(TOUR_STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setCompletedTours(new Set(parsed));
        } catch (e) {
          console.error('Failed to parse completed tours', e);
        }
      }
    }
  }, []);

  const startTour = useCallback((tourSteps: TourStep[]) => {
    setSteps(tourSteps);
    setCurrentStep(0);
    setIsActive(true);
  }, []);

  const nextStep = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      completeTour();
    }
  }, [currentStep, steps.length]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  const skipTour = useCallback(() => {
    setIsActive(false);
    setCurrentStep(0);
    setSteps([]);
  }, []);

  const completeTour = useCallback(() => {
    setIsActive(false);
    setCurrentStep(0);
    setSteps([]);
  }, []);

  const hasCompletedTour = useCallback(
    (tourId: string) => {
      return completedTours.has(tourId);
    },
    [completedTours],
  );

  const markTourComplete = useCallback(
    (tourId: string) => {
      const newCompleted = new Set(completedTours);
      newCompleted.add(tourId);
      setCompletedTours(newCompleted);

      if (typeof window !== 'undefined') {
        localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(Array.from(newCompleted)));
      }
    },
    [completedTours],
  );

  return (
    <TourContext.Provider
      value={{
        isActive,
        currentStep,
        steps,
        startTour,
        nextStep,
        prevStep,
        skipTour,
        completeTour,
        hasCompletedTour,
        markTourComplete,
      }}
    >
      {children}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (context === undefined) {
    throw new Error('useTour must be used within a TourProvider');
  }
  return context;
}
