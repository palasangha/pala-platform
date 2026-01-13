import React from 'react';
import { CheckCircle, AlertCircle, Clock } from 'lucide-react';

interface TimelineStep {
  step_number: number;
  provider: string;
  input_source: string;
  output_preview: string;
  processing_time_ms: number;
  confidence: number;
  success: boolean;
  error?: string;
  timestamp?: string;
}

interface ChainTimelineProps {
  steps: TimelineStep[];
  totalTimeMs: number;
  compact?: boolean;
  onStepClick?: (stepNumber: number) => void;
}

export const ChainTimeline: React.FC<ChainTimelineProps> = ({
  steps,
  totalTimeMs,
  compact = false,
  onStepClick,
}) => {
  const getProviderIcon = (provider: string): string => {
    const icons: Record<string, string> = {
      google_vision: '🔍',
      google_lens: '📷',
      azure: '☁️',
      tesseract: '📄',
      easyocr: '👁️',
      claude: '🤖',
      ollama: '🦙',
      vllm: '⚡',
      llamacpp: '💻',
    };
    return icons[provider] || '🔍';
  };

  const getProviderDisplayName = (provider: string): string => {
    const displayNames: Record<string, string> = {
      google_vision: 'Google Vision',
      google_lens: 'Google Lens',
      azure: 'Azure',
      tesseract: 'Tesseract',
      easyocr: 'EasyOCR',
      claude: 'Claude',
      ollama: 'Ollama',
      vllm: 'VLLM',
      llamacpp: 'llama.cpp',
    };
    return displayNames[provider] || provider;
  };

  const formatTime = (ms: number): string => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (compact) {
    // Compact horizontal timeline
    return (
      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-600">Chain Flow</div>
        <div className="flex items-center gap-2 flex-wrap">
          {steps.map((step, index) => (
            <React.Fragment key={step.step_number}>
              <button
                onClick={() => onStepClick?.(step.step_number)}
                className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  step.success
                    ? 'bg-green-100 text-green-800 hover:bg-green-200'
                    : 'bg-red-100 text-red-800 hover:bg-red-200'
                }`}
              >
                <span>{getProviderIcon(step.provider)}</span>
                <span>Step {step.step_number}</span>
              </button>
              {index < steps.length - 1 && <span className="text-gray-400">→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  }

  // Full timeline view
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Processing Timeline</h2>
        <div className="flex items-center gap-2 text-gray-600">
          <Clock size={16} />
          <span className="text-sm font-medium">Total: {formatTime(totalTimeMs)}</span>
        </div>
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={step.step_number} className="relative">
            {/* Timeline connector */}
            {index < steps.length - 1 && (
              <div className="absolute left-7 top-20 w-0.5 h-8 bg-gray-300"></div>
            )}

            {/* Step card */}
            <div
              className={`border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                step.success
                  ? 'bg-white border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
              onClick={() => onStepClick?.(step.step_number)}
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className="flex-shrink-0">
                  {step.success ? (
                    <CheckCircle size={24} className="text-green-500" />
                  ) : (
                    <AlertCircle size={24} className="text-red-500" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">
                      Step {step.step_number}
                    </h3>
                    <span className="text-sm text-gray-600">
                      {getProviderIcon(step.provider)} {getProviderDisplayName(step.provider)}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                    <span className="capitalize">{step.input_source.replace(/_/g, ' ')}</span>
                    <span>•</span>
                    <span>{formatTime(step.processing_time_ms)}</span>
                    {step.success && step.confidence > 0 && (
                      <>
                        <span>•</span>
                        <span>Confidence: {(step.confidence * 100).toFixed(1)}%</span>
                      </>
                    )}
                  </div>

                  {/* Output preview or error */}
                  {step.success && step.output_preview ? (
                    <div className="bg-gray-50 border border-gray-200 rounded p-3">
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {step.output_preview}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {step.output_preview.length} characters
                      </p>
                    </div>
                  ) : step.error ? (
                    <div className="bg-red-100 border border-red-300 rounded p-3">
                      <p className="text-sm text-red-800 font-medium">Error</p>
                      <p className="text-sm text-red-700">{step.error}</p>
                    </div>
                  ) : null}
                </div>

                {/* Status badge */}
                <div className="flex-shrink-0">
                  {step.success ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Success
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      Error
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mt-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm text-green-600 font-medium">Successful Steps</div>
          <div className="text-2xl font-bold text-green-900">
            {steps.filter((s) => s.success).length}
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600 font-medium">Avg Time/Step</div>
          <div className="text-2xl font-bold text-gray-900">
            {formatTime(totalTimeMs / steps.length)}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm text-blue-600 font-medium">Total Time</div>
          <div className="text-2xl font-bold text-blue-900">{formatTime(totalTimeMs)}</div>
        </div>
      </div>
    </div>
  );
};

export default ChainTimeline;
