'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useTour } from './tour-provider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function TourSpotlight() {
  const { isActive, currentStep, steps, nextStep, prevStep, skipTour } = useTour();
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const spotlightRef = useRef<HTMLDivElement>(null);

  const currentStepData = steps[currentStep];

  useEffect(() => {
    if (!isActive || !currentStepData) {
      setIsVisible(false);
      return;
    }

    // Find the target element
    const targetElement = document.querySelector(currentStepData.target);
    if (!targetElement) {
      console.warn(`Tour target not found: ${currentStepData.target}`);
      return;
    }

    // Get the element's position
    const rect = targetElement.getBoundingClientRect();
    setTargetRect(rect);
    setIsVisible(true);

    // Scroll element into view
    targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Execute step action if provided
    if (currentStepData.action) {
      currentStepData.action();
    }
  }, [isActive, currentStep, currentStepData]);

  if (!isActive || !isVisible || !targetRect || !currentStepData) {
    return null;
  }

  // Calculate tooltip position based on placement
  const getTooltipPosition = () => {
    const placement = currentStepData.placement || 'bottom';
    const padding = 16;
    const tooltipWidth = 320;

    switch (placement) {
      case 'top':
        return {
          top: targetRect.top - padding,
          left: targetRect.left + targetRect.width / 2,
          transform: 'translate(-50%, -100%)',
        };
      case 'bottom':
        return {
          top: targetRect.bottom + padding,
          left: targetRect.left + targetRect.width / 2,
          transform: 'translateX(-50%)',
        };
      case 'left':
        return {
          top: targetRect.top + targetRect.height / 2,
          left: targetRect.left - padding,
          transform: 'translate(-100%, -50%)',
        };
      case 'right':
        return {
          top: targetRect.top + targetRect.height / 2,
          left: targetRect.right + padding,
          transform: 'translateY(-50%)',
        };
      default:
        return {
          top: targetRect.bottom + padding,
          left: targetRect.left + targetRect.width / 2,
          transform: 'translateX(-50%)',
        };
    }
  };

  const tooltipPosition = getTooltipPosition();

  return (
    <>
      {/* Overlay */}
      <div className='fixed inset-0 z-[9998] pointer-events-none'>
        {/* Dark overlay with cutout */}
        <div className='absolute inset-0 bg-black/50' />

        {/* Spotlight cutout */}
        <div
          className='absolute bg-transparent border-4 border-blue-500 rounded-lg shadow-2xl pointer-events-auto'
          style={{
            top: targetRect.top - 4,
            left: targetRect.left - 4,
            width: targetRect.width + 8,
            height: targetRect.height + 8,
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.5)',
          }}
        />
      </div>

      {/* Tooltip */}
      <div
        ref={spotlightRef}
        className='fixed z-[9999]'
        style={{
          top: tooltipPosition.top,
          left: tooltipPosition.left,
          transform: tooltipPosition.transform,
          maxWidth: '320px',
        }}
      >
        <Card className='shadow-2xl border-2 border-blue-500'>
          <CardHeader className='pb-3'>
            <div className='flex items-start justify-between'>
              <div className='flex-1'>
                <CardTitle className='text-lg'>{currentStepData.title}</CardTitle>
                <CardDescription className='text-xs mt-1'>
                  Step {currentStep + 1} of {steps.length}
                </CardDescription>
              </div>
              <Button
                variant='ghost'
                size='icon'
                className='h-6 w-6 -mt-1 -mr-1'
                onClick={skipTour}
              >
                <X className='h-4 w-4' />
              </Button>
            </div>
          </CardHeader>
          <CardContent className='pb-4'>
            <p className='text-sm text-gray-600 mb-4'>{currentStepData.content}</p>

            <div className='flex items-center justify-between'>
              <Button variant='outline' size='sm' onClick={prevStep} disabled={currentStep === 0}>
                <ChevronLeft className='h-4 w-4 mr-1' />
                Back
              </Button>

              <div className='flex gap-1'>
                {steps.map((_, index) => (
                  <div
                    key={index}
                    className={cn(
                      'h-1.5 w-1.5 rounded-full transition-colors',
                      index === currentStep ? 'bg-blue-500' : 'bg-gray-300',
                    )}
                  />
                ))}
              </div>

              <Button size='sm' onClick={nextStep}>
                {currentStep === steps.length - 1 ? 'Finish' : 'Next'}
                {currentStep < steps.length - 1 && <ChevronRight className='h-4 w-4 ml-1' />}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
