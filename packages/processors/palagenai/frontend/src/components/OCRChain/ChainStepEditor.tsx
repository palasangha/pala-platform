import React, { useState, useEffect } from 'react';
import { ChevronDown, Trash2, Eye, EyeOff } from 'lucide-react';
import { ocrAPI } from '@/services/api';

interface ChainStep {
  step_number: number;
  provider: string;
  input_source: 'original_image' | 'previous_step' | 'step_N' | 'combined';
  input_step_numbers?: number[];
  prompt: string;
  enabled: boolean;
}

interface ChainStepEditorProps {
  step: ChainStep;
  stepNumber: number;
  totalSteps?: number;
  onUpdate: (step: ChainStep) => void;
  onDelete: () => void;
  showPromptHelp?: boolean;
}

export const ChainStepEditor: React.FC<ChainStepEditorProps> = ({
  step,
  stepNumber,
  onUpdate,
  onDelete,
  showPromptHelp = false,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    const loadProviders = async () => {
      try {
        const data = await ocrAPI.getProviders();
        setProviders(data.providers || []);
      } catch (error) {
        console.error('Failed to load providers:', error);
      } finally {
        setLoading(false);
      }
    };

    loadProviders();
  }, []);

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onUpdate({
      ...step,
      provider: e.target.value,
    });
  };

  const handleInputSourceChange = (
    source: 'original_image' | 'previous_step' | 'step_N' | 'combined'
  ) => {
    const newStep = { ...step, input_source: source };
    if (source === 'previous_step' && stepNumber === 1) {
      newStep.input_source = 'original_image';
    }
    onUpdate(newStep);
  };

  const handleInputStepToggle = (stepNum: number) => {
    const current = step.input_step_numbers || [];
    const updated = current.includes(stepNum)
      ? current.filter((n) => n !== stepNum)
      : [...current, stepNum].sort((a, b) => a - b);

    onUpdate({
      ...step,
      input_step_numbers: updated,
    });
  };

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onUpdate({
      ...step,
      prompt: e.target.value,
    });
  };

  const handleEnabledToggle = () => {
    onUpdate({
      ...step,
      enabled: !step.enabled,
    });
  };

  const getProviderDisplayName = (providerName: string) => {
    const displayNames: Record<string, string> = {
      google_vision: 'Google Cloud Vision',
      google_lens: 'Google Lens (Advanced)',
      serpapi_google_lens: 'Google Lens (SerpAPI)',
      chrome_lens: 'Chrome Lens (Local)',
      azure: 'Azure Computer Vision',
      ollama: 'Ollama (Gemma3)',
      vllm: 'VLLM',
      tesseract: 'Tesseract OCR',
      easyocr: 'EasyOCR',
      llamacpp: 'llama.cpp',
      claude: 'Claude AI',
    };
    return displayNames[providerName] || providerName;
  };

  const isAIProvider = (providerName: string) => {
    return ['claude', 'ollama', 'vllm', 'llamacpp'].includes(providerName);
  };

  return (
    <div
      className={`border rounded-lg transition-all ${
        step.enabled ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-300 opacity-60'
      }`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1">
          <ChevronDown
            size={20}
            className={`transition-transform ${expanded ? 'rotate-0' : '-rotate-90'}`}
          />
          <div className="flex-1">
            <div className="font-semibold text-gray-900">
              Step {stepNumber}: {getProviderDisplayName(step.provider || 'Select Provider')}
            </div>
            <div className="text-sm text-gray-500 capitalize">{step.input_source.replace('_', ' ')}</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={step.enabled}
              onChange={handleEnabledToggle}
              onClick={(e) => e.stopPropagation()}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-600">Enabled</span>
          </label>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete step"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="border-t border-gray-200 p-4 space-y-4">
          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">OCR Provider</label>
            <select
              value={step.provider}
              onChange={handleProviderChange}
              disabled={loading}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            >
              <option value="">Select a provider...</option>
              {providers.map((p) => (
                <option key={p.name} value={p.name} disabled={!p.available}>
                  {getProviderDisplayName(p.name)} {!p.available && '(Unavailable)'}
                </option>
              ))}
            </select>
          </div>

          {/* Input Source Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">Input Source</label>
            <div className="space-y-2">
              {/* Original Image */}
              <label className="flex items-center gap-3 p-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50">
                <input
                  type="radio"
                  checked={step.input_source === 'original_image'}
                  onChange={() => handleInputSourceChange('original_image')}
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-700">Original Image</span>
              </label>

              {/* Previous Step */}
              {stepNumber > 1 && (
                <label className="flex items-center gap-3 p-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50">
                  <input
                    type="radio"
                    checked={step.input_source === 'previous_step'}
                    onChange={() => handleInputSourceChange('previous_step')}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-gray-700">Output from Previous Step</span>
                </label>
              )}

              {/* Specific Step */}
              {stepNumber > 1 && (
                <div>
                  <label className="flex items-center gap-3 p-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50">
                    <input
                      type="radio"
                      checked={step.input_source === 'step_N'}
                      onChange={() => handleInputSourceChange('step_N')}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Specific Step Output</span>
                  </label>

                  {step.input_source === 'step_N' && (
                    <div className="mt-2 ml-7 p-2 bg-gray-50 rounded border border-gray-200">
                      <div className="text-xs text-gray-600 mb-2">Select step:</div>
                      <div className="flex flex-wrap gap-2">
                        {Array.from({ length: stepNumber - 1 }, (_, i) => i + 1).map((num) => (
                          <button
                            key={num}
                            onClick={() => handleInputStepToggle(num)}
                            className={`px-3 py-1 rounded text-sm transition-colors ${
                              (step.input_step_numbers || []).includes(num)
                                ? 'bg-blue-500 text-white'
                                : 'bg-white border border-gray-300 text-gray-700 hover:border-blue-500'
                            }`}
                          >
                            Step {num}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Combined Steps */}
              {stepNumber > 1 && (
                <div>
                  <label className="flex items-center gap-3 p-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50">
                    <input
                      type="radio"
                      checked={step.input_source === 'combined'}
                      onChange={() => handleInputSourceChange('combined')}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Combined Step Outputs</span>
                  </label>

                  {step.input_source === 'combined' && (
                    <div className="mt-2 ml-7 p-2 bg-gray-50 rounded border border-gray-200">
                      <div className="text-xs text-gray-600 mb-2">Select steps to combine:</div>
                      <div className="flex flex-wrap gap-2">
                        {Array.from({ length: stepNumber - 1 }, (_, i) => i + 1).map((num) => (
                          <button
                            key={num}
                            onClick={() => handleInputStepToggle(num)}
                            className={`px-3 py-1 rounded text-sm transition-colors ${
                              (step.input_step_numbers || []).includes(num)
                                ? 'bg-blue-500 text-white'
                                : 'bg-white border border-gray-300 text-gray-700 hover:border-blue-500'
                            }`}
                          >
                            Step {num}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Custom Prompt (for AI providers) */}
          {isAIProvider(step.provider) && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">Custom Prompt (Optional)</label>
                <button
                  onClick={() => setShowPrompt(!showPrompt)}
                  className="p-1 text-gray-500 hover:text-gray-700"
                  title="Show/hide prompt"
                >
                  {showPrompt ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <textarea
                value={showPrompt ? step.prompt : '••••••••'}
                onChange={handlePromptChange}
                placeholder="Enter a custom prompt for this step... (optional)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                rows={3}
                readOnly={!showPrompt}
              />
              {showPromptHelp && (
                <p className="mt-2 text-xs text-gray-500">
                  Tip: Use variables like {'{step_N_output}'} to reference previous step outputs
                </p>
              )}
            </div>
          )}

          {/* Input Info */}
          {step.input_source !== 'original_image' && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Input:</strong> This step will process text from{' '}
                {step.input_source === 'previous_step'
                  ? 'the previous step'
                  : step.input_source === 'step_N'
                  ? `step ${step.input_step_numbers?.join(', ')}`
                  : 'combined outputs'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChainStepEditor;
