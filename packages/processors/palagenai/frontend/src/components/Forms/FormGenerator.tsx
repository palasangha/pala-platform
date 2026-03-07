import { useState, useCallback } from 'react';
import { FormField } from './FormField';
import {
  FormSchema,
  imageMetadataSchema,
  getFieldsBySection,
} from '../../schemas/imageMetadataSchema';

interface FormGeneratorProps {
  data: Record<string, any>;
  schema?: FormSchema;
  onSubmit: (data: Record<string, any>) => Promise<void>;
  onCancel?: () => void;
  showReadOnly?: boolean;
}

export function FormGenerator({
  data,
  schema = imageMetadataSchema,
  onSubmit,
  onCancel,
  showReadOnly = true,
}: FormGeneratorProps) {
  const [formData, setFormData] = useState(data);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFieldChange = useCallback(
    (fieldName: string, value: any) => {
      setFormData((prev) => ({
        ...prev,
        [fieldName]: value,
      }));
      // Clear error for this field
      if (errors[fieldName]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[fieldName];
          return next;
        });
      }
    },
    [errors]
  );

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Filter out unchanged values
      const changes: Record<string, any> = {};
      for (const [key, value] of Object.entries(formData)) {
        if (JSON.stringify(value) !== JSON.stringify(data[key])) {
          changes[key] = value;
        }
      }

      if (Object.keys(changes).length === 0) {
        alert('No changes to save');
        return;
      }

      await onSubmit(changes);
      alert('Metadata updated successfully');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to update metadata';
      alert(`Error: ${message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Get fields organized by section
  const sectionedFields = getFieldsBySection();
  const sectionOrder = [
    'OCR & Content',
    'OCR Processing',
    'Document Information',
    'Correspondence',
    'Physical Attributes',
    'Analysis & Tags',
    'Storage & Access',
    'Advanced',
  ];

  const sections = sectionOrder
    .filter((section) => (sectionedFields[section] || []).length > 0)
    .map((section) => {
      const fieldsInSection = sectionedFields[section] || [];
      return (
        <div key={section} className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-200">
            {section}
          </h3>
          <div className="space-y-4">
            {fieldsInSection.map((fieldName) => {
              const fieldDef = schema[fieldName];
              if (!fieldDef) return null;
              if (!showReadOnly && fieldDef.readOnly) return null;

              return (
                <FormField
                  key={fieldName}
                  name={fieldName}
                  label={fieldDef.label}
                  definition={fieldDef}
                  value={formData[fieldName]}
                  onChange={(value) => handleFieldChange(fieldName, value)}
                  error={errors[fieldName]}
                />
              );
            })}
          </div>
        </div>
      );
    });

  return (
    <div>
      {sections}

      <div className="flex items-center justify-end gap-3 mt-8 pt-6 border-t border-gray-200">
        {onCancel && (
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {isSubmitting && (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          Save Changes
        </button>
      </div>
    </div>
  );
}
