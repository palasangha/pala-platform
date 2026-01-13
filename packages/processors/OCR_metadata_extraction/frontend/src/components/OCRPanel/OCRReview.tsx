import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ocrAPI } from '@/services/api';
import type { Image, OCRProvider } from '@/types';
import { ArrowLeft, Play, Save, RefreshCw, ZoomIn, ZoomOut, FileJson, ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import Editor from '@monaco-editor/react';
import { FormGenerator } from '@/components/Forms/FormGenerator';

// Extend window interface for storing project images
declare global {
  interface Window {
    __projectImages?: any[];
  }
}

export const OCRReview: React.FC = () => {
  const { projectId, imageId } = useParams<{ projectId: string; imageId: string }>();
  const navigate = useNavigate();
  const [imageIndex, setImageIndex] = useState(0);
  const [totalImages, setTotalImages] = useState(0);

  const [image, setImage] = useState<Image | null>(null);
  const [imageUrl, setImageUrl] = useState<string>('');
  const [ocrText, setOcrText] = useState('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [languages, setLanguages] = useState<string[]>(['en', 'hi']);
  const [handwriting, setHandwriting] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [providers, setProviders] = useState<OCRProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('google_vision');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [showPromptEditor, setShowPromptEditor] = useState(false);

  // JSON Editor state
  const [jsonText, setJsonText] = useState<string>('');
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [showMetadataForm, setShowMetadataForm] = useState(false);
  const [jsonError, setJsonError] = useState<string>('');
  const [jsonHasChanges, setJsonHasChanges] = useState(false);

  // Monaco JSON Editor state
  const [monacoJsonText, setMonacoJsonText] = useState<string>('');
  const [monacoJsonError, setMonacoJsonError] = useState<string>('');
  const [monacoHasChanges, setMonacoHasChanges] = useState(false);
  const [savingJson, setSavingJson] = useState(false);
  const [pushingToArchipelago, setPushingToArchipelago] = useState(false);
  const [archipelagoSuccess, setArchipelagoSuccess] = useState<string>('');

  // Zoom and pan state
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const imageContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (imageId) {
      loadImageData();
      if (projectId) {
        loadProjectImages();
      }
    }
  }, [imageId, projectId]);

  const loadProjectImages = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/images`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setTotalImages(data.images.length);
        const currentIndex = data.images.findIndex((img: any) => img.id === imageId);
        setImageIndex(currentIndex !== -1 ? currentIndex + 1 : 0);

        // Store images list for navigation
        window.__projectImages = data.images;
      }
    } catch (err) {
      console.log('Failed to load project images');
    }
  };

  const handleNavigateToImage = (nextImageId: string) => {
    if (projectId && nextImageId) {
      navigate(`/projects/${projectId}/images/${nextImageId}`);
    }
  };

  const handlePreviousImage = () => {
    if (window.__projectImages && imageIndex > 1) {
      const prevImage = window.__projectImages[imageIndex - 2]; // -1 for 0-indexed, -1 more for previous
      if (prevImage) {
        handleNavigateToImage(prevImage.id);
      }
    }
  };

  const handleNextImage = () => {
    if (window.__projectImages && imageIndex < totalImages) {
      const nextImage = window.__projectImages[imageIndex]; // imageIndex is 1-based, so this is the next image
      if (nextImage) {
        handleNavigateToImage(nextImage.id);
      }
    }
  };

  // Prevent page scrolling when zooming image with mouse wheel
  useEffect(() => {
    const container = imageContainerRef.current;
    if (!container || image?.file_type === 'pdf') return;

    const handleWheelCapture = (e: WheelEvent) => {
      // Prevent page scroll when mouse is over the image container
      e.preventDefault();
      e.stopPropagation();

      // Handle zoom
      const delta = e.deltaY * -0.001;
      setScale((prevScale) => {
        const newScale = Math.min(Math.max(0.5, prevScale + delta), 5);

        // Reset position when zooming out to 1x
        if (newScale === 1) {
          setPosition({ x: 0, y: 0 });
        }

        return newScale;
      });
    };

    // Add listener with { passive: false } to allow preventDefault
    container.addEventListener('wheel', handleWheelCapture, { passive: false });

    return () => {
      container.removeEventListener('wheel', handleWheelCapture);
    };
  }, [image, imageUrl]); // Re-register when image loads

  useEffect(() => {
    loadProviders();
    // Initialize prompt on load
    const defaultPrompt = getDefaultPrompt(selectedProvider, languages, handwriting);
    setCustomPrompt(defaultPrompt);
    setShowPromptEditor(true);
  }, []);

  // Update prompt when languages or handwriting settings change
  useEffect(() => {
    const defaultPrompt = getDefaultPrompt(selectedProvider, languages, handwriting);
    setCustomPrompt(defaultPrompt);
  }, [languages, handwriting]);

  const loadProviders = async () => {
    try {
      const { providers: availableProviders } = await ocrAPI.getProviders();
      setProviders(availableProviders);

      // Set default provider to the first available one
      const defaultProvider = availableProviders.find(p => p.available);
      if (defaultProvider) {
        setSelectedProvider(defaultProvider.name);
      }
    } catch (err) {
      console.error('Failed to load OCR providers', err);
    }
  };

  const loadImageData = async () => {
    if (!imageId) return;

    try {
      // Load image details
      const imageDetails = await ocrAPI.getImageDetails(imageId);
      setImage(imageDetails.image);
      setOcrText(imageDetails.image.ocr_text || '');

      // Initialize JSON data from image metadata
      initializeJsonData(imageDetails.image);

      // Load image blob with proper authorization
      try {
        const imageBlob = await ocrAPI.getImage(imageId);
        const blobUrl = URL.createObjectURL(imageBlob);
        setImageUrl(blobUrl);
        console.log('Image loaded successfully');
      } catch (blobErr: any) {
        console.error('Error loading image blob:', {
          status: blobErr.response?.status,
          error: blobErr.response?.data?.error,
          message: blobErr.message
        });
        setError(`Failed to load image file: ${blobErr.response?.data?.error || blobErr.message}`);
      }
    } catch (err: any) {
      console.error('Error loading image details:', {
        status: err.response?.status,
        error: err.response?.data?.error,
        message: err.message
      });
      setError(`Failed to load image data: ${err.response?.data?.error || err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const initializeJsonData = (imageData: Image) => {
    // Structure data according to required format: metadata, document, content, analysis
    const data: any = {
      metadata: {
        id: imageData.id,
        collection_id: imageData.project_id,
        document_type: imageData.metadata?.document_type || 'letter',
        storage_location: {
          archive_name: imageData.metadata?.archive_name || '',
          collection_name: imageData.metadata?.collection_name || '',
          box_number: imageData.metadata?.box_number || '',
          folder_number: imageData.metadata?.folder_number || '',
          digital_repository: imageData.filepath,
        },
        digitization_info: {
          date: imageData.ocr_processed_at || imageData.created_at,
          operator: imageData.metadata?.operator || '',
          equipment: imageData.metadata?.equipment || '',
          resolution: imageData.metadata?.resolution || '',
          file_format: imageData.file_type,
        },
        access_level: imageData.metadata?.access_level || 'private',
        ocr_provider: imageData.provider,
        confidence: imageData.confidence,
      },
      document: {
        date: {
          creation_date: imageData.metadata?.creation_date || imageData.created_at,
          sent_date: imageData.metadata?.sent_date || null,
          received_date: imageData.metadata?.received_date || null,
        },
        reference_number: imageData.metadata?.reference_number || '',
        languages: imageData.languages || imageData.detected_language ? [imageData.detected_language] : [],
        physical_attributes: {
          size: imageData.metadata?.size || '',
          material: imageData.metadata?.material || '',
          condition: imageData.metadata?.condition || '',
          letterhead: imageData.metadata?.letterhead || '',
          pages: imageData.pages_processed || imageData.metadata?.pages || null,
        },
        correspondence: {
          sender: {
            name: imageData.metadata?.sender_name || '',
            title: imageData.metadata?.sender_title || '',
            affiliation: imageData.metadata?.sender_affiliation || '',
            location: imageData.metadata?.sender_location || '',
            contact_info: {
              address: imageData.metadata?.sender_address || '',
              telephone: imageData.metadata?.sender_telephone || '',
              fax: imageData.metadata?.sender_fax || '',
              email: imageData.metadata?.sender_email || '',
            },
            biography: imageData.metadata?.sender_biography || '',
          },
          recipient: {
            name: imageData.metadata?.recipient_name || '',
            title: imageData.metadata?.recipient_title || '',
            affiliation: imageData.metadata?.recipient_affiliation || '',
            location: imageData.metadata?.recipient_location || '',
            contact_info: {
              address: imageData.metadata?.recipient_address || '',
              telephone: imageData.metadata?.recipient_telephone || '',
              fax: imageData.metadata?.recipient_fax || '',
              email: imageData.metadata?.recipient_email || '',
            },
            biography: imageData.metadata?.recipient_biography || '',
          },
          cc: imageData.metadata?.cc || [],
        },
      },
      content: {
        full_text: imageData.ocr_text || '',
        summary: imageData.metadata?.summary || '',
        salutation: imageData.metadata?.salutation || '',
        body: imageData.metadata?.body || (imageData.ocr_text ? [imageData.ocr_text] : []),
        closing: imageData.metadata?.closing || '',
        signature: imageData.metadata?.signature || '',
        attachments: imageData.metadata?.attachments || [],
        annotations: imageData.metadata?.annotations || [],
      },
      analysis: {
        keywords: imageData.metadata?.keywords || [],
        subjects: imageData.metadata?.subjects || [],
        events: imageData.metadata?.events || [],
        locations: imageData.metadata?.locations || [],
        people: imageData.metadata?.people || [],
        organizations: imageData.metadata?.organizations || [],
        historical_context: imageData.metadata?.historical_context || '',
        significance: imageData.metadata?.significance || '',
        relationships: imageData.metadata?.relationships || [],
      },
      ocr_processing: {
        status: imageData.ocr_status,
        blocks_count: imageData.blocks_count,
        words_count: imageData.words_count,
        handwriting_detected: imageData.handwriting,
        retry_count: imageData.retry_count,
        intermediate_images: imageData.intermediate_images,
      },
      timestamps: {
        created_at: imageData.created_at,
        updated_at: imageData.updated_at,
        ocr_processed_at: imageData.ocr_processed_at,
      },
    };

    const jsonString = JSON.stringify(data, null, 2);
    setJsonText(jsonString);
    setMonacoJsonText(jsonString);
    setJsonError('');
    setMonacoJsonError('');
  };

  const handleJsonChange = (text: string) => {
    setJsonText(text);
    setJsonHasChanges(true);
    setJsonError('');

    // Try to parse to validate
    try {
      JSON.parse(text);
      setJsonError('');
    } catch (e: any) {
      setJsonError(e.message);
    }
  };

  const handleSaveJson = async () => {
    if (!imageId || jsonError) return;

    try {
      const parsedData = JSON.parse(jsonText);

      // Extract the OCR text and update it
      const newOcrText = parsedData.ocr_text || '';
      const updated = await ocrAPI.updateImageText(imageId, newOcrText);

      setImage(updated.image);
      setOcrText(newOcrText);
      setJsonHasChanges(false);

      // Update JSON view with latest data
      initializeJsonData(updated.image);

      setError('');
    } catch (err: any) {
      setError(`Failed to save JSON: ${err.message}`);
    }
  };

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setJsonError('');
    } catch (e: any) {
      setJsonError(`Invalid JSON: ${e.message}`);
    }
  };

  const handleMonacoChange = (value: string | undefined) => {
    if (value === undefined) return;

    setMonacoJsonText(value);
    setMonacoHasChanges(true);
    setMonacoJsonError('');
    setArchipelagoSuccess('');

    // Validate JSON
    try {
      JSON.parse(value);
    } catch (e: any) {
      setMonacoJsonError(e.message);
    }
  };

  const handleSaveMonacoJson = async () => {
    if (!imageId || monacoJsonError) return;

    setSavingJson(true);
    setError('');

    try {
      const parsedData = JSON.parse(monacoJsonText);

      // Transform hierarchical structure to flat API format
      const apiPayload: any = {};

      // Extract top-level fields
      if (parsedData.content?.full_text) apiPayload.ocr_text = parsedData.content.full_text;
      if (parsedData.ocr_processing?.status) apiPayload.ocr_status = parsedData.ocr_processing.status;

      // Build metadata object from all the nested fields
      const metadata: any = {};

      // Flatten content section
      if (parsedData.content) {
        metadata.summary = parsedData.content.summary;
        metadata.salutation = parsedData.content.salutation;
        metadata.body = parsedData.content.body;
        metadata.closing = parsedData.content.closing;
        metadata.signature = parsedData.content.signature;
        metadata.attachments = parsedData.content.attachments;
        metadata.annotations = parsedData.content.annotations;
      }

      // Flatten document section
      if (parsedData.document) {
        if (parsedData.document.date) {
          metadata.creation_date = parsedData.document.date.creation_date;
          metadata.sent_date = parsedData.document.date.sent_date;
          metadata.received_date = parsedData.document.date.received_date;
        }
        metadata.reference_number = parsedData.document.reference_number;

        if (parsedData.document.physical_attributes) {
          metadata.size = parsedData.document.physical_attributes.size;
          metadata.material = parsedData.document.physical_attributes.material;
          metadata.condition = parsedData.document.physical_attributes.condition;
          metadata.letterhead = parsedData.document.physical_attributes.letterhead;
          metadata.pages = parsedData.document.physical_attributes.pages;
        }

        if (parsedData.document.correspondence) {
          if (parsedData.document.correspondence.sender) {
            metadata.sender_name = parsedData.document.correspondence.sender.name;
            metadata.sender_title = parsedData.document.correspondence.sender.title;
            metadata.sender_affiliation = parsedData.document.correspondence.sender.affiliation;
            metadata.sender_location = parsedData.document.correspondence.sender.location;
            metadata.sender_biography = parsedData.document.correspondence.sender.biography;
            if (parsedData.document.correspondence.sender.contact_info) {
              metadata.sender_address = parsedData.document.correspondence.sender.contact_info.address;
              metadata.sender_telephone = parsedData.document.correspondence.sender.contact_info.telephone;
              metadata.sender_fax = parsedData.document.correspondence.sender.contact_info.fax;
              metadata.sender_email = parsedData.document.correspondence.sender.contact_info.email;
            }
          }

          if (parsedData.document.correspondence.recipient) {
            metadata.recipient_name = parsedData.document.correspondence.recipient.name;
            metadata.recipient_title = parsedData.document.correspondence.recipient.title;
            metadata.recipient_affiliation = parsedData.document.correspondence.recipient.affiliation;
            metadata.recipient_location = parsedData.document.correspondence.recipient.location;
            metadata.recipient_biography = parsedData.document.correspondence.recipient.biography;
            if (parsedData.document.correspondence.recipient.contact_info) {
              metadata.recipient_address = parsedData.document.correspondence.recipient.contact_info.address;
              metadata.recipient_telephone = parsedData.document.correspondence.recipient.contact_info.telephone;
              metadata.recipient_fax = parsedData.document.correspondence.recipient.contact_info.fax;
              metadata.recipient_email = parsedData.document.correspondence.recipient.contact_info.email;
            }
          }

          metadata.cc = parsedData.document.correspondence.cc;
        }
      }

      // Flatten metadata section
      if (parsedData.metadata) {
        metadata.document_type = parsedData.metadata.document_type;
        metadata.access_level = parsedData.metadata.access_level;
        if (parsedData.metadata.storage_location) {
          metadata.archive_name = parsedData.metadata.storage_location.archive_name;
          metadata.collection_name = parsedData.metadata.storage_location.collection_name;
          metadata.box_number = parsedData.metadata.storage_location.box_number;
          metadata.folder_number = parsedData.metadata.storage_location.folder_number;
        }
        if (parsedData.metadata.digitization_info) {
          metadata.operator = parsedData.metadata.digitization_info.operator;
          metadata.equipment = parsedData.metadata.digitization_info.equipment;
          metadata.resolution = parsedData.metadata.digitization_info.resolution;
        }
      }

      // Flatten analysis section
      if (parsedData.analysis) {
        metadata.keywords = parsedData.analysis.keywords;
        metadata.subjects = parsedData.analysis.subjects;
        metadata.events = parsedData.analysis.events;
        metadata.locations = parsedData.analysis.locations;
        metadata.people = parsedData.analysis.people;
        metadata.organizations = parsedData.analysis.organizations;
        metadata.historical_context = parsedData.analysis.historical_context;
        metadata.significance = parsedData.analysis.significance;
        metadata.relationships = parsedData.analysis.relationships;
      }

      // Only add metadata if it has content
      if (Object.keys(metadata).some(key => metadata[key] !== undefined && metadata[key] !== null)) {
        apiPayload.metadata = metadata;
      }

      const updated = await ocrAPI.updateImageJSON(imageId, apiPayload);

      setImage(updated.image);
      setOcrText(updated.image.ocr_text || '');
      setMonacoHasChanges(false);
      initializeJsonData(updated.image);

      alert('JSON saved successfully!');
    } catch (err: any) {
      setError(`Failed to save JSON: ${err.message}`);
    } finally {
      setSavingJson(false);
    }
  };

  const handlePushToArchipelago = async () => {
    if (!imageId || !image) return;

    if (monacoHasChanges) {
      if (!confirm('You have unsaved JSON changes. Do you want to save them first?')) {
        return;
      }
      await handleSaveMonacoJson();
    }

    setPushingToArchipelago(true);
    setError('');
    setArchipelagoSuccess('');

    try {
      const result = await ocrAPI.pushToArchipelago(imageId, {
        title: image.original_filename,
        tags: [],
        custom_metadata: {}
      });

      if (result.success) {
        setArchipelagoSuccess(
          `Document pushed successfully! View at: ${result.archipelago_url}`
        );
      } else {
        setError('Failed to push to Archipelago');
      }
    } catch (err: any) {
      setError(`Failed to push to Archipelago: ${err.response?.data?.error || err.message}`);
    } finally {
      setPushingToArchipelago(false);
    }
  };

  const handleProcessOCR = async () => {
    if (!imageId) return;

    setProcessing(true);
    setError('');

    try {
      const processOptions: any = {
        languages,
        handwriting,
        provider: selectedProvider,
      };

      // Include custom prompt for all providers
      if (customPrompt) {
        processOptions.custom_prompt = customPrompt;
      }

      const result = await ocrAPI.processImage(imageId, processOptions);
      setOcrText(result.text);
      setHasChanges(false);

      // Reload image details to update status
      const imageDetails = await ocrAPI.getImageDetails(imageId);
      setImage(imageDetails.image);
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'OCR processing failed';
      console.error('OCR Processing Error:', err);
      setError(errorMsg);
    } finally {
      setProcessing(false);
    }
  };

  const handleSaveText = async () => {
    if (!imageId) return;

    setSaving(true);
    try {
      const updated = await ocrAPI.updateImageText(imageId, ocrText);
      setImage(updated.image);
      setHasChanges(false);
    } catch (err) {
      setError('Failed to save text');
    } finally {
      setSaving(false);
    }
  };

  const handleTextChange = (text: string) => {
    setOcrText(text);
    setHasChanges(true);
  };

  const toggleLanguage = (lang: string) => {
    if (languages.includes(lang)) {
      setLanguages(languages.filter((l) => l !== lang));
    } else {
      setLanguages([...languages, lang]);
    }
  };

  const getDefaultPrompt = (provider: string, langs: string[], hw: boolean): string => {
    const langNames: { [key: string]: string } = {
      en: 'English',
      hi: 'Hindi',
      es: 'Spanish',
      fr: 'French',
      de: 'German',
      zh: 'Chinese',
      ja: 'Japanese',
      ar: 'Arabic',
    };

    const langList = langs.map((l) => langNames[l] || l).join(', ');

    let prompt = 'Extract all text from this image accurately. ';

    if (hw) {
      prompt += 'The image contains handwritten text. ';
    }

    if (langs.length > 0) {
      prompt += `The text may be in ${langList}. `;
    }

    prompt += 'Provide only the extracted text without any explanations or additional commentary. Maintain the original formatting and line breaks.';
    if (provider === 'google_vision') {
      prompt += ' Use Google Cloud Vision OCR for extraction.';
    } 
    return prompt;
  };

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    // Update default prompt when provider changes
    const defaultPrompt = getDefaultPrompt(provider, languages, handwriting);
    setCustomPrompt(defaultPrompt);
    setShowPromptEditor(true); // Show for all providers
  };

  // Mouse handlers for pan/drag
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (scale > 1) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isDragging && scale > 1) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  const resetZoom = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow z-10">
        <div className="max-w-full px-4 sm:px-6 lg:px-8 py-4">
          {/* Top row: Back button and file navigation */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <button
                onClick={() => navigate(`/projects/${projectId}`)}
                className="mr-4 text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900">OCR Review</h1>
                <p className="text-sm text-gray-600">{image?.original_filename}</p>
              </div>
            </div>

            {/* File navigation */}
            {totalImages > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  File {imageIndex} of {totalImages}
                </span>
                <button
                  onClick={handlePreviousImage}
                  disabled={imageIndex <= 1}
                  className="p-1 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Previous image"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={handleNextImage}
                  disabled={imageIndex >= totalImages}
                  className="p-1 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Next image"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div></div>

            <div className="flex items-center space-x-4">
              {/* OCR Provider Selection */}
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Provider:</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {providers.map((provider) => (
                    <option
                      key={provider.name}
                      value={provider.name}
                      disabled={!provider.available}
                    >
                      {provider.display_name} {!provider.available && '(Unavailable)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Language Selection */}
              <div className="flex items-center space-x-2">
                <label className="flex items-center space-x-1">
                  <input
                    type="checkbox"
                    checked={languages.includes('en')}
                    onChange={() => toggleLanguage('en')}
                    className="rounded"
                  />
                  <span className="text-sm">English</span>
                </label>
                <label className="flex items-center space-x-1">
                  <input
                    type="checkbox"
                    checked={languages.includes('hi')}
                    onChange={() => toggleLanguage('hi')}
                    className="rounded"
                  />
                  <span className="text-sm">Hindi</span>
                </label>
              </div>

              {/* Handwriting Toggle */}
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={handwriting}
                  onChange={(e) => setHandwriting(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Handwriting</span>
              </label>

              {/* Action Buttons */}
              <button
                onClick={handleProcessOCR}
                disabled={processing || languages.length === 0}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {processing ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                {processing ? 'Processing...' : 'Process OCR'}
              </button>

              <button
                onClick={handleSaveText}
                disabled={saving || !hasChanges}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>

              <button
                onClick={() => setShowJsonEditor(!showJsonEditor)}
                className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                <FileJson className="w-4 h-4 mr-2" />
                {showJsonEditor ? 'Hide JSON' : 'Edit JSON'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Custom Prompt Editor for All Providers */}
          {showPromptEditor && (
            <div className="mt-4 border-t pt-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Custom Prompt {(selectedProvider === 'ollama' || selectedProvider === 'vllm' || selectedProvider === 'claude') ? '' : '(Informational - not used by this provider)'}
                </label>
                <button
                  onClick={() => {
                    const defaultPrompt = getDefaultPrompt(selectedProvider, languages, handwriting);
                    setCustomPrompt(defaultPrompt);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Reset to Default
                </button>
              </div>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
                rows={3}
                placeholder="Enter a custom prompt to guide the OCR process..."
              />
              <p className="text-xs text-gray-500 mt-1">
                {(selectedProvider === 'ollama' || selectedProvider === 'vllm' || selectedProvider === 'claude')
                  ? 'Edit this prompt to customize how the AI extracts text from your image.'
                  : 'This prompt describes the OCR task but is not used by traditional OCR providers (Google Vision, Azure, Tesseract, EasyOCR).'}
              </p>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Container - Scrollable */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Twin Panel Layout */}
        <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Original Image or PDF */}
        <div
          className="flex-1 bg-gray-900 flex items-center justify-center p-4 overflow-hidden relative"
          ref={imageContainerRef}
          onMouseDown={image?.file_type !== 'pdf' ? handleMouseDown : undefined}
          onMouseMove={image?.file_type !== 'pdf' ? handleMouseMove : undefined}
          onMouseUp={image?.file_type !== 'pdf' ? handleMouseUp : undefined}
          onMouseLeave={image?.file_type !== 'pdf' ? handleMouseLeave : undefined}
          style={{ cursor: image?.file_type !== 'pdf' && scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
        >
          {image?.file_type === 'pdf' ? (
            // PDF Display using iframe
            <div className="w-full h-full flex items-center justify-center">
              {imageUrl ? (
                <iframe
                  src={imageUrl}
                  title="PDF Document"
                  className="w-full h-full border-none"
                  style={{ display: 'block' }}
                />
              ) : (
                <div className="text-white">Failed to load PDF</div>
              )}
            </div>
          ) : (
            // Image Display with zoom and pan
            <div
              className="max-w-full max-h-full"
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                transformOrigin: 'center',
                transition: isDragging ? 'none' : 'transform 0.1s ease-out',
              }}
            >
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt="Original"
                  className="max-w-full max-h-full object-contain select-none"
                  draggable={false}
                />
              ) : (
                <div className="text-white">Failed to load image</div>
              )}
            </div>
          )}

          {/* Zoom Controls Overlay - Only for Images */}
          {image?.file_type !== 'pdf' && (
            <div className="absolute top-4 right-4 bg-black bg-opacity-70 text-white px-3 py-2 rounded-md text-sm flex items-center space-x-2">
              <ZoomOut className="w-4 h-4" />
              <span className="font-mono">{Math.round(scale * 100)}%</span>
              <ZoomIn className="w-4 h-4" />
              {scale !== 1 && (
                <>
                  <div className="w-px h-4 bg-gray-400"></div>
                  <button
                    onClick={resetZoom}
                    className="text-xs hover:text-blue-400 transition-colors"
                  >
                    Reset
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-1 bg-gray-300"></div>

        {/* Right Panel - OCR Text or JSON Editor or Metadata Form */}
        <div className="flex-1 bg-white flex flex-col">
          {/* Tabs */}
          <div className="border-b bg-gray-50">
            <div className="flex">
              <button
                onClick={() => {
                  setShowJsonEditor(false);
                  setShowMetadataForm(false);
                }}
                className={`px-4 py-3 font-medium text-sm border-b-2 ${
                  !showJsonEditor && !showMetadataForm
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center">
                  <Play className="w-4 h-4 mr-2" />
                  OCR Text
                </div>
              </button>
              <button
                onClick={() => {
                  setShowJsonEditor(false);
                  setShowMetadataForm(true);
                }}
                className={`px-4 py-3 font-medium text-sm border-b-2 ${
                  showMetadataForm
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center">
                  <Settings className="w-4 h-4 mr-2" />
                  Metadata
                </div>
              </button>
              <button
                onClick={() => {
                  setShowJsonEditor(true);
                  setShowMetadataForm(false);
                }}
                className={`px-4 py-3 font-medium text-sm border-b-2 ${
                  showJsonEditor && !showMetadataForm
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center">
                  <FileJson className="w-4 h-4 mr-2" />
                  JSON Editor
                </div>
              </button>
            </div>
          </div>

          {!showJsonEditor && !showMetadataForm ? (
            /* OCR Text View */
            <>
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold text-gray-900">OCR Text</h2>
                <p className="text-sm text-gray-600">
                  Status: <span className="capitalize">{image?.ocr_status}</span>
                </p>
              </div>

              <div className="flex-1 p-4">
                <textarea
                  value={ocrText}
                  onChange={(e) => handleTextChange(e.target.value)}
                  className="w-full h-full p-4 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-none"
                  placeholder="OCR text will appear here after processing..."
                />
              </div>

              {hasChanges && (
                <div className="p-4 bg-yellow-50 border-t border-yellow-200">
                  <p className="text-sm text-yellow-800">
                    You have unsaved changes. Click "Save Changes" to save your edits.
                  </p>
                </div>
              )}
            </>
          ) : showMetadataForm ? (
            /* Metadata Form View */
            <>
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold text-gray-900">Metadata Editor</h2>
                <p className="text-sm text-gray-600">
                  Edit image metadata using a structured form
                </p>
              </div>

              <div className="flex-1 p-4 overflow-y-auto">
                {image && (
                  <FormGenerator
                    data={image}
                    onSubmit={async (changes) => {
                      // Transform flat form fields into API-compatible structure
                      const apiPayload: any = {};

                      // Top-level OCR fields
                      if ('ocr_text' in changes) apiPayload.ocr_text = changes.ocr_text;
                      if ('summary' in changes) {
                        if (!apiPayload.metadata) apiPayload.metadata = {};
                        apiPayload.metadata.summary = changes.summary;
                      }

                      // Build metadata object with all other fields
                      const metadataFields = [
                        'document_type', 'creation_date', 'reference_number',
                        'sender_name', 'sender_title', 'sender_affiliation', 'sender_location', 'sender_address', 'sender_telephone', 'sender_fax', 'sender_email', 'sender_biography',
                        'recipient_name', 'recipient_title', 'recipient_affiliation', 'recipient_location', 'recipient_address', 'recipient_telephone', 'recipient_fax', 'recipient_email', 'recipient_biography',
                        'pages', 'material', 'condition',
                        'keywords', 'subjects', 'historical_context', 'significance',
                        'access_level', 'archive_name', 'collection_name', 'box_number', 'folder_number',
                        'salutation', 'closing', 'signature', 'attachments', 'annotations', 'cc', 'events', 'locations', 'people', 'organizations', 'relationships'
                      ];

                      metadataFields.forEach(field => {
                        if (field in changes) {
                          if (!apiPayload.metadata) apiPayload.metadata = {};
                          apiPayload.metadata[field] = changes[field];
                        }
                      });

                      // Only send if there are changes
                      if (Object.keys(apiPayload).length === 0) {
                        alert('No changes to save');
                        return;
                      }

                      try {
                        await ocrAPI.updateImageJSON(imageId!, apiPayload);
                        const imageDetails = await ocrAPI.getImageDetails(imageId!);
                        setImage(imageDetails.image);
                        initializeJsonData(imageDetails.image);
                        alert('Metadata updated successfully');
                      } catch (error: any) {
                        const errorMsg = error.response?.data?.error || error.message || 'Failed to update metadata';
                        alert(`Error: ${errorMsg}`);
                        throw error;
                      }
                    }}
                    showReadOnly={true}
                  />
                )}
              </div>
            </>
          ) : (
            /* JSON Editor View */
            <>
              <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">JSON Editor</h2>
                    <p className="text-sm text-gray-600">
                      Edit the complete OCR result metadata
                    </p>
                  </div>
                  <button
                    onClick={handleFormatJson}
                    className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                  >
                    Format JSON
                  </button>
                </div>
              </div>

              <div className="flex-1 p-4 overflow-hidden flex flex-col">
                <textarea
                  value={jsonText}
                  onChange={(e) => handleJsonChange(e.target.value)}
                  className={`flex-1 w-full p-4 border rounded-md focus:outline-none focus:ring-2 font-mono text-sm resize-none ${
                    jsonError
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                  placeholder="JSON will appear here..."
                  spellCheck={false}
                />

                {jsonError && (
                  <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                    <p className="text-sm text-red-700">
                      <span className="font-semibold">JSON Error:</span> {jsonError}
                    </p>
                  </div>
                )}

                {!jsonError && jsonHasChanges && (
                  <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-sm text-yellow-700">
                      ✓ Valid JSON. Click "Save JSON" to save changes.
                    </p>
                  </div>
                )}
              </div>

              <div className="p-4 border-t bg-gray-50 flex items-center justify-between">
                <div className="text-xs text-gray-600">
                  {jsonHasChanges && !jsonError && '✓ Changes ready to save'}
                  {jsonError && '✗ Fix JSON errors before saving'}
                </div>
                <button
                  onClick={handleSaveJson}
                  disabled={!jsonHasChanges || !!jsonError}
                  className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Save className="w-4 h-4 mr-2" />
                  Save JSON
                </button>
              </div>
            </>
          )}
        </div>
      </div>
      {/* End Twin Panels */}

      {/* Monaco JSON Editor Panel */}
      <div className="border-t-2 border-gray-300 bg-gray-50 flex flex-col" style={{ height: '500px', minHeight: '500px' }}>
        {/* Monaco Editor Header */}
        <div className="px-4 py-3 border-b bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Full JSON Editor (Monaco)
              </h2>
              <p className="text-sm text-gray-600">
                Edit complete image metadata with syntax highlighting and validation
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSaveMonacoJson}
                disabled={!monacoHasChanges || !!monacoJsonError || savingJson}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4 mr-2" />
                {savingJson ? 'Saving...' : 'Save JSON'}
              </button>

              <button
                onClick={handlePushToArchipelago}
                disabled={pushingToArchipelago || !image?.ocr_text}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                title={!image?.ocr_text ? 'Process OCR first before pushing to Archipelago' : 'Push this document to Archipelago Commons'}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${pushingToArchipelago ? 'animate-spin' : ''}`} />
                {pushingToArchipelago ? 'Pushing...' : 'Push to Archipelago'}
              </button>
            </div>
          </div>
        </div>

        {/* Monaco Editor */}
        <div className="flex-1 p-4 overflow-hidden">
          <Editor
            height="100%"
            defaultLanguage="json"
            value={monacoJsonText}
            onChange={handleMonacoChange}
            theme="vs-light"
            options={{
              minimap: { enabled: true },
              fontSize: 13,
              lineNumbers: 'on',
              rulers: [80],
              wordWrap: 'on',
              wrappingIndent: 'indent',
              formatOnPaste: true,
              formatOnType: true,
              autoClosingBrackets: 'always',
              autoClosingQuotes: 'always',
              scrollBeyondLastLine: false,
              tabSize: 2,
            }}
          />
        </div>

        {/* Status Messages */}
        <div className="p-4 border-t bg-gray-50">
          {monacoJsonError && (
            <div className="mb-2 p-3 bg-red-50 border border-red-200 rounded">
              <p className="text-sm text-red-700">
                <span className="font-semibold">JSON Error:</span> {monacoJsonError}
              </p>
            </div>
          )}

          {!monacoJsonError && monacoHasChanges && (
            <div className="mb-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-sm text-yellow-700">
                Valid JSON with unsaved changes. Click "Save JSON" to persist.
              </p>
            </div>
          )}

          {archipelagoSuccess && (
            <div className="mb-2 p-3 bg-green-50 border border-green-200 rounded">
              <p className="text-sm text-green-700">
                {archipelagoSuccess}
              </p>
            </div>
          )}

          <div className="text-xs text-gray-600 flex items-center justify-between">
            <span>
              {monacoHasChanges && !monacoJsonError && 'Changes ready to save'}
              {monacoJsonError && 'Fix JSON errors before saving'}
              {!monacoHasChanges && !monacoJsonError && 'No unsaved changes'}
            </span>
            <span>
              Lines: {monacoJsonText.split('\n').length} |
              Characters: {monacoJsonText.length}
            </span>
          </div>
        </div>
      </div>
      {/* End scrollable content */}
      </div>
    </div>
  );
};
