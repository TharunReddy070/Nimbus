import React, { useState, useEffect } from 'react';
import { ProcessingSteps } from './ProcessingSteps';

interface Step {
  id: number;
  message: string;
  status: 'completed' | 'current' | 'pending';
}

interface ProcessingStepsHandlerProps {
  isProcessing: boolean;
  onComplete: () => void;
  steps: { message: string }[];
}

export function ProcessingStepsHandler({ isProcessing, onComplete, steps }: ProcessingStepsHandlerProps) {
  const [visibleSteps, setVisibleSteps] = useState<Step[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [shouldShow, setShouldShow] = useState(false);

  // Reset everything when processing starts or steps change
  useEffect(() => {
    if (isProcessing && steps.length > 0) {
      setShouldShow(true);
      
      // Convert API steps to our UI Step format
      const uiSteps = steps.map((step, index) => ({
        id: index + 1,
        message: step.message,
        status: index === steps.length - 1 ? 'current' as const : 'completed' as const
      }));
      
      setVisibleSteps(uiSteps);
      
      // If we have all steps, consider it complete after a short delay
      if (steps.length === 4) { // Assuming we have 4 total steps
        setTimeout(() => {
          setIsComplete(true);
          // Signal completion
          setTimeout(() => {
            onComplete();
          }, 1000);
        }, 500);
      }
    } else if (!isProcessing) {
      // Reset when processing is done
      setVisibleSteps([]);
      setIsComplete(false);
      setShouldShow(false);
    }
  }, [isProcessing, steps, onComplete]);

  if (!shouldShow) return null;

  return (
    <div className="w-full max-w-2xl mx-auto my-4 border-2 border-gray-300 rounded-lg p-4 shadow-md">
      <ProcessingSteps
        steps={visibleSteps}
        isComplete={isComplete}
        isCollapsed={isComplete}
      />
    </div>
  );
} 