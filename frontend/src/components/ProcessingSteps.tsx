import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import { CSSTransition } from 'react-transition-group';

interface Step {
  id: number;
  message: string;
  status: 'completed' | 'current' | 'pending';
}

interface ProcessingStepsProps {
  steps: Step[];
  isComplete: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: (isCollapsed: boolean) => void;
}

export function ProcessingSteps({ 
  steps, 
  isComplete, 
  isCollapsed: defaultCollapsed = false,
  onToggleCollapse 
}: ProcessingStepsProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (defaultCollapsed !== undefined) {
      setIsCollapsed(defaultCollapsed);
    }
  }, [defaultCollapsed]);

  useEffect(() => {
    // Calculate progress based on completed steps
    const completedSteps = steps.filter(s => s.status === 'completed').length;
    const currentStep = steps.findIndex(s => s.status === 'current');
    const totalSteps = steps.length;
    
    let newProgress = (completedSteps / totalSteps) * 100;
    if (currentStep !== -1) {
      newProgress += (1 / totalSteps) * 50; // Add half progress for current step
    }
    
    setProgress(newProgress);
  }, [steps]);

  const handleToggleCollapse = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    onToggleCollapse?.(newState);
  };

  if (steps.length === 0) return null;

  return (
    <div className="processing-steps">
      <div className="processing-steps-header">
        <div className="flex items-center space-x-2">
          <span>Processing Step</span>
          {isComplete && (
            <span className="text-green-500 flex items-center space-x-1">
              <CheckCircle className="w-4 h-4" />
              <span>Complete</span>
            </span>
          )}
        </div>
        <button
          onClick={handleToggleCollapse}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
        >
          {isCollapsed ? (
            <ChevronDown className="w-5 h-5" />
          ) : (
            <ChevronUp className="w-5 h-5" />
          )}
        </button>
      </div>

      <CSSTransition
        in={!isCollapsed}
        timeout={300}
        classNames="steps-collapse"
        unmountOnExit
      >
        <div className="processing-steps-content">
          {/* Flowing line */}
          <div className="flowing-line">
            <div 
              className="flowing-line-progress"
              style={{ height: `${progress}%` }}
            />
          </div>

          {/* Steps */}
          <div className="">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`step-item ${
                  step.status === 'current' ? 'step-current' :
                  step.status === 'completed' ? 'step-completed' : ''
                }`}
                style={{ animationDelay: `${index * 150}ms` }}
              >
                <div className="step-dot">
                  <div className="step-dot-outer">
                    <div className="step-dot-inner" />
                  </div>
                </div>
                <div className="step-content">
                  {step.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CSSTransition>
    </div>
  );
}