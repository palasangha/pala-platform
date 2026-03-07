import { X } from 'lucide-react';
import { FieldDefinition } from '../../schemas/imageMetadataSchema';
import { useState } from 'react';

interface FormFieldProps {
  name: string;
  label: string;
  definition: FieldDefinition;
  value: any;
  onChange: (value: any) => void;
  error?: string;
}

export function FormField({
  label,
  definition,
  value,
  onChange,
  error,
}: FormFieldProps) {
  const [jsonError, setJsonError] = useState<string>('');

  const isDisabled = definition.readOnly;

  const renderField = () => {
    switch (definition.type) {
      case 'text':
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={definition.placeholder}
            disabled={isDisabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
        );

      case 'textarea':
        return (
          <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={definition.placeholder}
            disabled={isDisabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            style={{ minHeight: '150px', resize: 'vertical' }}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            disabled={isDisabled}
            min={definition.min}
            max={definition.max}
            step={definition.step}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
        );

      case 'select':
        return (
          <select
            value={value || ''}
            onChange={(e) => onChange(e.target.value || null)}
            disabled={isDisabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          >
            <option value="">Select {label}</option>
            {definition.options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        return (
          <MultiSelectField
            options={definition.options || []}
            selectedValues={value || []}
            onChange={onChange}
            isDisabled={isDisabled}
          />
        );

      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => onChange(e.target.checked)}
              disabled={isDisabled}
              className="w-4 h-4 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <span className="text-sm">{label}</span>
          </label>
        );

      case 'json':
        return (
          <JsonField
            value={value}
            onChange={onChange}
            isDisabled={isDisabled}
            onError={setJsonError}
          />
        );

      default:
        return <div className="text-red-500 text-sm">Unknown field type: {definition.type}</div>;
    }
  };

  return (
    <div className="mb-4">
      {definition.type !== 'boolean' && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {definition.readOnly && (
            <span className="ml-2 text-xs text-gray-500">(read-only)</span>
          )}
        </label>
      )}

      {renderField()}

      {definition.description && definition.type !== 'boolean' && (
        <p className="text-xs text-gray-600 mt-1">{definition.description}</p>
      )}

      {error && (
        <p className="text-red-500 text-xs mt-1">{error}</p>
      )}

      {jsonError && (
        <p className="text-red-500 text-xs mt-1">{jsonError}</p>
      )}
    </div>
  );
}

interface MultiSelectFieldProps {
  options: { label: string; value: any }[];
  selectedValues: any[];
  onChange: (values: any[]) => void;
  isDisabled?: boolean;
}

function MultiSelectField({
  options,
  selectedValues,
  onChange,
  isDisabled,
}: MultiSelectFieldProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {selectedValues?.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() =>
              onChange(selectedValues.filter((v) => v !== value))
            }
            disabled={isDisabled}
            className="inline-flex items-center gap-1 px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {options.find((opt) => opt.value === value)?.label || value}
            <X size={14} />
          </button>
        ))}
      </div>

      <select
        onChange={(e) => {
          if (e.target.value && !selectedValues.includes(e.target.value)) {
            onChange([...selectedValues, e.target.value]);
            (e.target as HTMLSelectElement).value = '';
          }
        }}
        disabled={isDisabled}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
      >
        <option value="">Add language...</option>
        {options
          .filter((opt) => !selectedValues.includes(opt.value))
          .map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
      </select>
    </div>
  );
}

interface JsonFieldProps {
  value: Record<string, any> | undefined;
  onChange: (value: Record<string, any>) => void;
  isDisabled?: boolean;
  onError: (error: string) => void;
}

function JsonField({ value, onChange, isDisabled, onError }: JsonFieldProps) {
  const [text, setText] = useState(() =>
    value ? JSON.stringify(value, null, 2) : ''
  );

  const handleChange = (newText: string) => {
    setText(newText);
    try {
      if (!newText.trim()) {
        onChange({});
        onError('');
      } else {
        const parsed = JSON.parse(newText);
        onChange(typeof parsed === 'object' ? parsed : {});
        onError('');
      }
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Invalid JSON');
    }
  };

  return (
    <div
      className={`border border-gray-300 rounded-md overflow-hidden ${
        isDisabled ? 'bg-gray-50' : 'bg-white'
      }`}
    >
      <textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        disabled={isDisabled}
        className="w-full px-3 py-2 font-mono text-xs focus:outline-none disabled:bg-gray-100"
        style={{ minHeight: '120px', resize: 'vertical', border: 'none' }}
        placeholder="{}"
      />
    </div>
  );
}
