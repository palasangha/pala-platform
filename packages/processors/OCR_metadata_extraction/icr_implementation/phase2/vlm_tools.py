"""
Phase 2: VLM Tools for Document Analysis
=========================================
Vision-Language Model tools for analyzing charts, tables, and figures.
Based on L3 notebook implementation with LangChain integration.

Author: ICR Integration Team
Date: 2026-01-23
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import base64
from io import BytesIO

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMTools:
    """
    Vision-Language Model tools for document understanding.
    
    Provides specialized tools for analyzing:
    - Charts and graphs
    - Tables with complex structure
    - Figures and diagrams
    
    Uses VLM models (GPT-4V, Claude-3, etc.) for intelligent analysis.
    """
    
    def __init__(self, 
                 provider: str = 'openai',
                 model: str = 'gpt-4o-mini',
                 api_key: Optional[str] = None):
        """
        Initialize VLM tools.
        
        Args:
            provider: VLM provider ('openai', 'anthropic')
            model: Model name
            api_key: Optional API key (uses env var if not provided)
        """
        logger.info("=" * 80)
        logger.info("Initializing VLM Tools")
        logger.info("=" * 80)
        logger.info(f"Provider: {provider}")
        logger.info(f"Model: {model}")
        
        self.provider = provider
        self.model = model
        self.api_key = api_key
        
        try:
            if provider == 'openai':
                import openai
                if api_key:
                    openai.api_key = api_key
                self.client = openai
                logger.info("✓ OpenAI client initialized")
                
            elif provider == 'anthropic':
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("✓ Anthropic client initialized")
            
            self.initialized = True
            logger.info("=" * 80)
            
        except ImportError as e:
            logger.warning(f"VLM provider not available: {e}")
            logger.warning("Tools will return mock responses")
            self.client = None
            self.initialized = False
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            raise
    
    def analyze_chart(self, 
                     image_path: str,
                     region_bbox: Optional[List[float]] = None,
                     query: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a chart or graph using VLM.
        
        Args:
            image_path: Path to image containing chart
            region_bbox: Optional bounding box [x1, y1, x2, y2] to crop
            query: Optional specific question about the chart
            
        Returns:
            Dictionary with chart analysis results
        """
        logger.info("=" * 80)
        logger.info("Analyzing Chart with VLM")
        logger.info("=" * 80)
        logger.info(f"Image: {image_path}")
        if region_bbox:
            logger.info(f"Region: {region_bbox}")
        
        start_time = time.time()
        
        # Crop region if specified
        if region_bbox:
            image_data = self._crop_region(image_path, region_bbox)
        else:
            image_data = self._load_image(image_path)
        
        # Default query if not provided
        if not query:
            query = """Analyze this chart and provide:
1. Chart type (bar, line, pie, scatter, etc.)
2. Title and labels (x-axis, y-axis, legend)
3. Key data points and trends
4. Summary of what the chart shows"""
        
        # Call VLM
        logger.info("Sending request to VLM...")
        if self.client and self.initialized:
            result = self._call_vlm(image_data, query, analysis_type='chart')
        else:
            result = self._mock_chart_analysis(image_path, query)
        
        process_time = time.time() - start_time
        result['processing_time'] = process_time
        
        logger.info("=" * 80)
        logger.info("Chart Analysis Complete:")
        logger.info(f"  Chart Type: {result.get('chart_type', 'N/A')}")
        logger.info(f"  Processing Time: {process_time:.2f}s")
        logger.info("=" * 80)
        
        return result
    
    def analyze_table(self,
                     image_path: str,
                     region_bbox: Optional[List[float]] = None,
                     extract_as: str = 'dict') -> Dict[str, Any]:
        """
        Analyze a table and extract structured data.
        
        Args:
            image_path: Path to image containing table
            region_bbox: Optional bounding box [x1, y1, x2, y2] to crop
            extract_as: Output format ('dict', 'csv', 'markdown')
            
        Returns:
            Dictionary with table data and metadata
        """
        logger.info("=" * 80)
        logger.info("Analyzing Table with VLM")
        logger.info("=" * 80)
        logger.info(f"Image: {image_path}")
        logger.info(f"Output Format: {extract_as}")
        
        start_time = time.time()
        
        # Crop region if specified
        if region_bbox:
            image_data = self._crop_region(image_path, region_bbox)
        else:
            image_data = self._load_image(image_path)
        
        # Build query based on desired format
        query = f"""Extract the table data from this image.
Provide the result as {extract_as}.

Include:
1. Column headers
2. All row data
3. Any merged cells or special formatting
4. Table caption if present"""
        
        # Call VLM
        logger.info("Sending request to VLM...")
        if self.client and self.initialized:
            result = self._call_vlm(image_data, query, analysis_type='table')
        else:
            result = self._mock_table_analysis(image_path, extract_as)
        
        process_time = time.time() - start_time
        result['processing_time'] = process_time
        
        logger.info("=" * 80)
        logger.info("Table Analysis Complete:")
        logger.info(f"  Rows: {result.get('num_rows', 'N/A')}")
        logger.info(f"  Columns: {result.get('num_columns', 'N/A')}")
        logger.info(f"  Processing Time: {process_time:.2f}s")
        logger.info("=" * 80)
        
        return result
    
    def analyze_figure(self,
                      image_path: str,
                      region_bbox: Optional[List[float]] = None,
                      query: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a figure, diagram, or illustration.
        
        Args:
            image_path: Path to image containing figure
            region_bbox: Optional bounding box [x1, y1, x2, y2] to crop
            query: Optional specific question about the figure
            
        Returns:
            Dictionary with figure analysis results
        """
        logger.info("=" * 80)
        logger.info("Analyzing Figure with VLM")
        logger.info("=" * 80)
        logger.info(f"Image: {image_path}")
        
        start_time = time.time()
        
        # Crop region if specified
        if region_bbox:
            image_data = self._crop_region(image_path, region_bbox)
        else:
            image_data = self._load_image(image_path)
        
        # Default query if not provided
        if not query:
            query = """Analyze this figure and provide:
1. Type of figure (diagram, flowchart, photo, illustration, etc.)
2. Main components or elements
3. Relationships between elements
4. Caption or title if present
5. Brief description of what it shows"""
        
        # Call VLM
        logger.info("Sending request to VLM...")
        if self.client and self.initialized:
            result = self._call_vlm(image_data, query, analysis_type='figure')
        else:
            result = self._mock_figure_analysis(image_path, query)
        
        process_time = time.time() - start_time
        result['processing_time'] = process_time
        
        logger.info("=" * 80)
        logger.info("Figure Analysis Complete:")
        logger.info(f"  Figure Type: {result.get('figure_type', 'N/A')}")
        logger.info(f"  Processing Time: {process_time:.2f}s")
        logger.info("=" * 80)
        
        return result
    
    def _call_vlm(self,
                 image_data: bytes,
                 query: str,
                 analysis_type: str) -> Dict[str, Any]:
        """
        Call VLM API with image and query.
        
        Args:
            image_data: Image bytes
            query: Analysis query
            analysis_type: Type of analysis (chart, table, figure)
            
        Returns:
            Analysis results
        """
        if self.provider == 'openai':
            return self._call_openai(image_data, query, analysis_type)
        elif self.provider == 'anthropic':
            return self._call_anthropic(image_data, query, analysis_type)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _call_openai(self,
                    image_data: bytes,
                    query: str,
                    analysis_type: str) -> Dict[str, Any]:
        """Call OpenAI Vision API."""
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Parse response based on analysis type
            result = {
                'raw_response': content,
                'analysis_type': analysis_type,
                'model': self.model,
                'provider': self.provider
            }
            
            # Try to extract structured data
            if analysis_type == 'chart':
                result.update(self._parse_chart_response(content))
            elif analysis_type == 'table':
                result.update(self._parse_table_response(content))
            elif analysis_type == 'figure':
                result.update(self._parse_figure_response(content))
            
            return result
            
        except Exception as e:
            logger.error(f"VLM API call failed: {e}", exc_info=True)
            return {'error': str(e), 'analysis_type': analysis_type}
    
    def _call_anthropic(self,
                       image_data: bytes,
                       query: str,
                       analysis_type: str) -> Dict[str, Any]:
        """Call Anthropic Claude API."""
        # Similar implementation for Claude
        logger.warning("Anthropic provider not fully implemented yet")
        return self._mock_chart_analysis('image', query)
    
    def _load_image(self, image_path: str) -> bytes:
        """Load image file as bytes."""
        with open(image_path, 'rb') as f:
            return f.read()
    
    def _crop_region(self, 
                    image_path: str, 
                    bbox: List[float]) -> bytes:
        """Crop region from image."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(image_path)
            x1, y1, x2, y2 = [int(c) for c in bbox]
            
            cropped = img[y1:y2, x1:x2]
            
            # Encode to PNG bytes
            success, encoded = cv2.imencode('.png', cropped)
            if success:
                return encoded.tobytes()
            else:
                raise ValueError("Failed to encode cropped image")
                
        except ImportError:
            logger.warning("OpenCV not available, using full image")
            return self._load_image(image_path)
    
    def _mock_chart_analysis(self, image_path: str, query: str) -> Dict[str, Any]:
        """Mock chart analysis for testing."""
        logger.info("Using mock chart analysis (VLM not available)")
        return {
            'chart_type': 'bar_chart',
            'title': 'Sample Chart',
            'x_axis_label': 'Categories',
            'y_axis_label': 'Values',
            'data_points': [
                {'category': 'A', 'value': 10},
                {'category': 'B', 'value': 25},
                {'category': 'C', 'value': 15}
            ],
            'summary': 'A bar chart showing values for categories A, B, and C',
            'mock': True
        }
    
    def _mock_table_analysis(self, image_path: str, extract_as: str) -> Dict[str, Any]:
        """Mock table analysis for testing."""
        logger.info("Using mock table analysis (VLM not available)")
        return {
            'num_rows': 3,
            'num_columns': 3,
            'headers': ['Column 1', 'Column 2', 'Column 3'],
            'data': [
                ['Value 1.1', 'Value 1.2', 'Value 1.3'],
                ['Value 2.1', 'Value 2.2', 'Value 2.3'],
                ['Value 3.1', 'Value 3.2', 'Value 3.3']
            ],
            'format': extract_as,
            'mock': True
        }
    
    def _mock_figure_analysis(self, image_path: str, query: str) -> Dict[str, Any]:
        """Mock figure analysis for testing."""
        logger.info("Using mock figure analysis (VLM not available)")
        return {
            'figure_type': 'diagram',
            'components': ['Element A', 'Element B', 'Element C'],
            'description': 'A diagram showing the relationship between three elements',
            'caption': 'Sample Figure',
            'mock': True
        }
    
    def _parse_chart_response(self, response: str) -> Dict[str, Any]:
        """Parse VLM response for chart analysis."""
        # Simple parsing - could be enhanced with structured output
        return {
            'chart_type': 'unknown',
            'summary': response
        }
    
    def _parse_table_response(self, response: str) -> Dict[str, Any]:
        """Parse VLM response for table extraction."""
        return {
            'num_rows': 0,
            'num_columns': 0,
            'data': [],
            'raw': response
        }
    
    def _parse_figure_response(self, response: str) -> Dict[str, Any]:
        """Parse VLM response for figure analysis."""
        return {
            'figure_type': 'unknown',
            'description': response
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get VLM tools statistics."""
        return {
            'service': 'VLM Tools',
            'provider': self.provider,
            'model': self.model,
            'initialized': self.initialized,
            'tools': [
                'analyze_chart',
                'analyze_table',
                'analyze_figure'
            ]
        }


def main():
    """Test VLM tools."""
    logger.info("\n" + "=" * 80)
    logger.info("VLM Tools Test")
    logger.info("=" * 80 + "\n")
    
    # Initialize tools (will use mock mode without API key)
    tools = VLMTools(provider='openai', model='gpt-4o-mini')
    stats = tools.get_stats()
    
    logger.info("Tools Statistics:")
    logger.info(json.dumps(stats, indent=2))
    
    logger.info("\nNote: VLM tools initialized in mock mode")
    logger.info("To use real VLM: set OPENAI_API_KEY environment variable")


if __name__ == '__main__':
    main()
