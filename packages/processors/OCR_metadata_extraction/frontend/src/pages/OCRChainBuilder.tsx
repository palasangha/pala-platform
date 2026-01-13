import React, { useState, useEffect } from 'react';
import { Plus, Play, FolderOpen, Save, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import AppLayout from '@/components/Layout/AppLayout';
import ChainStepEditor from '@/components/OCRChain/ChainStepEditor';
import FolderPicker from '@/components/OCRChain/FolderPicker';
import { chainAPI } from '@/services/api';
import { useNavigate } from 'react-router-dom';

interface ChainStep {
  step_number: number;
  provider: string;
  input_source: 'original_image' | 'previous_step' | 'step_N' | 'combined';
  input_step_numbers?: number[];
  prompt: string;
  enabled: boolean;
}

interface ChainTemplate {
  id: string;
  name: string;
  description: string;
  steps: ChainStep[];
}

export default function OCRChainBuilder() {
  const navigate = useNavigate();
  const [steps, setSteps] = useState<ChainStep[]>([
    {
      step_number: 1,
      provider: 'google_vision',
      input_source: 'original_image',
      prompt: '',
      enabled: true,
    },
  ]);
  const [folderPath, setFolderPath] = useState('');
  const [templates, setTemplates] = useState<ChainTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState<{ type: 'error' | 'success' | 'info'; text: string } | null>(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const data = await chainAPI.getTemplates(0, 50);
      setTemplates(data.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
      setMessage({ type: 'error', text: 'Failed to load templates' });
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleAddStep = () => {
    const newStepNumber = Math.max(...steps.map((s) => s.step_number), 0) + 1;
    setSteps([
      ...steps,
      {
        step_number: newStepNumber,
        provider: 'tesseract',
        input_source: newStepNumber > 1 ? 'previous_step' : 'original_image',
        prompt: '',
        enabled: true,
      },
    ]);
  };

  const handleDeleteStep = (stepNumber: number) => {
    if (steps.length === 1) {
      setMessage({ type: 'error', text: 'Chain must have at least one step' });
      return;
    }
    setSteps(steps.filter((s) => s.step_number !== stepNumber));
  };

  const handleUpdateStep = (stepNumber: number, updatedStep: ChainStep) => {
    setSteps(steps.map((s) => (s.step_number === stepNumber ? updatedStep : s)));
  };

  const handleLoadTemplate = async (templateId: string) => {
    try {
      const data = await chainAPI.getTemplate(templateId);
      setSteps(data.template.steps);
      setSelectedTemplate(templateId);
      setMessage({ type: 'success', text: 'Template loaded successfully' });
    } catch (error) {
      console.error('Failed to load template:', error);
      setMessage({ type: 'error', text: 'Failed to load template' });
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      setMessage({ type: 'error', text: 'Please enter a template name' });
      return;
    }

    try {
      await chainAPI.createTemplate({
        name: templateName,
        description: templateDescription,
        steps,
        is_public: false,
      });
      setMessage({ type: 'success', text: 'Template saved successfully' });
      setShowSaveTemplate(false);
      setTemplateName('');
      setTemplateDescription('');
      await loadTemplates();
    } catch (error) {
      console.error('Failed to save template:', error);
      setMessage({ type: 'error', text: 'Failed to save template' });
    }
  };

  const handleFolderSelected = (path: string) => {
    setFolderPath(path);
    setShowFolderPicker(false);
    setMessage({ type: 'success', text: `Folder selected: ${path}` });
  };

  const handleStartProcessing = async () => {
    if (!folderPath.trim()) {
      setMessage({ type: 'error', text: 'Please select a folder' });
      return;
    }

    try {
      setIsProcessing(true);
      const result = await chainAPI.startChainJob({
        folder_path: folderPath,
        chain_config: {
          template_id: selectedTemplate || undefined,
          steps,
        },
        languages: ['en'],
        handwriting: false,
        recursive: true,
        export_formats: ['json', 'csv', 'text'],
      });

      setMessage({ type: 'success', text: 'Chain job started successfully' });
      // Navigate to results page
      setTimeout(() => {
        navigate(`/ocr-chains/results/${result.job_id}`);
      }, 1000);
    } catch (error: any) {
      console.error('Failed to start chain job:', error);
      const errorMessage =
        error.response?.data?.error || 'Failed to start chain job';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setIsProcessing(false);
    }
  };

  const sortedSteps = [...steps].sort((a, b) => a.step_number - b.step_number);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">OCR Provider Chaining</h1>
          <p className="text-gray-600">
            Create a chain of OCR providers to process images sequentially
          </p>
        </div>

        {/* Message Alert */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg flex items-gap gap-3 ${
              message.type === 'error'
                ? 'bg-red-50 border border-red-200 text-red-800'
                : message.type === 'success'
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-blue-50 border border-blue-200 text-blue-800'
            }`}
          >
            {message.type === 'error' ? (
              <AlertCircle size={20} className="flex-shrink-0" />
            ) : (
              <CheckCircle size={20} className="flex-shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Sidebar - Templates & Folder */}
          <div className="lg:col-span-1 space-y-6">
            {/* Template Selector */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-3">Templates</h2>

              {loadingTemplates ? (
                <div className="flex items-center justify-center py-4">
                  <Loader size={20} className="animate-spin text-gray-400" />
                </div>
              ) : templates.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => handleLoadTemplate(template.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                        selectedTemplate === template.id
                          ? 'bg-blue-100 border border-blue-300 text-blue-900'
                          : 'border border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-sm font-medium truncate">{template.name}</div>
                      <div className="text-xs text-gray-500">{template.steps.length} steps</div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 py-4">No templates saved yet</p>
              )}
            </div>

            {/* Folder Selection */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-3">Input Folder</h2>
              <button
                onClick={() => setShowFolderPicker(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-gray-700"
              >
                <FolderOpen size={20} />
                <span>Browse Folder</span>
              </button>
              <input
                type="text"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="Or paste path here..."
                className="mt-3 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Save Template Button */}
            <button
              onClick={() => setShowSaveTemplate(!showSaveTemplate)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors font-medium"
            >
              <Save size={20} />
              Save as Template
            </button>

            {/* Start Processing Button */}
            <button
              onClick={handleStartProcessing}
              disabled={isProcessing || !folderPath.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
            >
              {isProcessing ? (
                <>
                  <Loader size={20} className="animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Play size={20} />
                  <span>Start Chain</span>
                </>
              )}
            </button>
          </div>

          {/* Main Content - Chain Steps */}
          <div className="lg:col-span-3 space-y-4">
            {/* Steps Header */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Chain Steps ({steps.filter((s) => s.enabled).length}/{steps.length})
              </h2>
              <button
                onClick={handleAddStep}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                <Plus size={20} />
                Add Step
              </button>
            </div>

            {/* Steps List */}
            <div className="space-y-3">
              {sortedSteps.map((step) => (
                <ChainStepEditor
                  key={step.step_number}
                  step={step}
                  stepNumber={step.step_number}
                  totalSteps={steps.length}
                  onUpdate={(updated) => handleUpdateStep(step.step_number, updated)}
                  onDelete={() => handleDeleteStep(step.step_number)}
                  showPromptHelp={true}
                />
              ))}
            </div>

            {/* Chain Flow Info */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
              <h3 className="font-semibold text-blue-900 mb-2">Chain Flow</h3>
              <div className="flex items-center gap-2 flex-wrap text-sm text-blue-800">
                {sortedSteps.map((step, index) => (
                  <React.Fragment key={step.step_number}>
                    <div className="bg-white border border-blue-300 rounded px-2 py-1">
                      <span className="font-medium">Step {step.step_number}</span>
                    </div>
                    {index < sortedSteps.length - 1 && (
                      <span className="text-blue-600 font-bold">→</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Folder Picker Modal */}
        {showFolderPicker && (
          <FolderPicker
            onSelect={handleFolderSelected}
            onClose={() => setShowFolderPicker(false)}
          />
        )}

        {/* Save Template Modal */}
        {showSaveTemplate && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 space-y-4">
              <h2 className="text-xl font-bold text-gray-900">Save Chain as Template</h2>

              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="Template name..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />

              <textarea
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value)}
                placeholder="Description (optional)..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowSaveTemplate(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTemplate}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                >
                  Save Template
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
