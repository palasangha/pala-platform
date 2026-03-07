"""
Comprehensive tests for AMIFilenameGenerator.

Covers:
1.  Full happy path — all fields present → correct filename
2.  Missing fields — each field missing one at a time → XXXX in right position
3.  All fields missing → XXXX_XXXX_XXXX_XXXX_XXXX_XXXX_TO_XXXX.JPG
4.  Document type mapping — all types + unknown
5.  Medium mapping — all medium types + unknown
6.  Original filename parsing — AMI-format extracts master_id and sequence
7.  Non-AMI original filename — master_id/sequence fallback to XXXX
8.  Name formatting — Unicode, mixed case, extra spaces, numbers in name
9.  Extension handling — .jpg, .JPG, .png, .tiff, no extension
10. Year extraction — from temporal_markers, from ISO date string, missing
11. Component dict — all keys present in output
12. Integration with bulk_processor result — generated_filename in result
13. Integration with data_mapper — merge_enriched_with_ocr output
"""

import pytest
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ami_filename_generator import AMIFilenameGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_enriched(
    document_type='letter',
    medium='mixed',
    year='1990',
    sender='BK MODI',
    recipient='REVSNGOENKA',
):
    """Build a minimal enriched data dict with all main fields populated."""
    enriched = {}
    if document_type is not None:
        enriched['metadata'] = {'document_type': document_type}
    if any(v is not None for v in (medium, year, sender, recipient)):
        enriched['document'] = {}
    doc = enriched.get('document', {})

    if medium is not None:
        doc['physical_attributes'] = {'medium': medium}
    if year is not None:
        doc['date'] = {'temporal_markers': {'year': year}}
    if sender is not None:
        doc.setdefault('correspondence', {})['sender'] = {'name': sender}
    if recipient is not None:
        doc.setdefault('correspondence', {})['recipient'] = {'name': recipient}

    if doc:
        enriched['document'] = doc
    return enriched


AMI_ORIGINAL = 'MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG'
AMI_MASTER_ID = 'MSALTMEBA00100004.00'
AMI_SEQUENCE = '(01_02_0071)'


# ---------------------------------------------------------------------------
# 1. Full happy path
# ---------------------------------------------------------------------------

class TestFullHappyPath:
    def test_complete_filename(self):
        gen = AMIFilenameGenerator()
        enriched = make_enriched()
        result = gen.generate(enriched, AMI_ORIGINAL)
        fn = result['generated_filename']
        assert fn == f'{AMI_MASTER_ID}_{AMI_SEQUENCE}_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG'

    def test_returns_dict_with_expected_keys(self):
        gen = AMIFilenameGenerator()
        result = gen.generate(make_enriched(), AMI_ORIGINAL)
        assert 'generated_filename' in result
        assert 'components' in result


# ---------------------------------------------------------------------------
# 2. Missing fields — one at a time
# ---------------------------------------------------------------------------

class TestMissingFields:
    def test_missing_document_type(self):
        enriched = make_enriched(document_type=None)
        result = AMIFilenameGenerator().generate(enriched, AMI_ORIGINAL)
        parts = result['generated_filename'].split('_')
        # Segment 3 (0-indexed after split on _): after sequence segment
        assert result['components']['document_type'] == 'XX'
        assert '_XX_' in result['generated_filename']

    def test_missing_medium(self):
        enriched = make_enriched(medium=None)
        result = AMIFilenameGenerator().generate(enriched, AMI_ORIGINAL)
        assert result['components']['medium'] == 'XXXX'
        assert '_XXXX_' in result['generated_filename']

    def test_missing_year(self):
        # Use a plain filename with no year so the filename-fallback doesn't fire
        enriched = make_enriched(year=None)
        result = AMIFilenameGenerator().generate(enriched, 'scan001.jpg')
        assert result['components']['year'] == 'XXXX'
        assert '_XXXX_' in result['generated_filename']

    def test_missing_sender(self):
        enriched = make_enriched(sender=None)
        result = AMIFilenameGenerator().generate(enriched, AMI_ORIGINAL)
        assert result['components']['sender'] == 'XXXX'
        assert 'XXXX_TO_' in result['generated_filename']

    def test_missing_recipient(self):
        enriched = make_enriched(recipient=None)
        result = AMIFilenameGenerator().generate(enriched, AMI_ORIGINAL)
        assert result['components']['recipient'] == 'XXXX'
        assert '_TO_XXXX' in result['generated_filename']

    def test_missing_original_filename_master_id(self):
        result = AMIFilenameGenerator().generate(make_enriched(), original_filename='plain_file.jpg')
        assert result['components']['master_identifier'] == 'XXXX'

    def test_missing_original_filename_sequence(self):
        result = AMIFilenameGenerator().generate(make_enriched(), original_filename='plain_file.jpg')
        assert result['components']['sequence'] == '(XXXX_XXXX_XXXX)'


# ---------------------------------------------------------------------------
# 3. All fields missing
# ---------------------------------------------------------------------------

class TestAllFieldsMissing:
    def test_all_xxxx(self):
        result = AMIFilenameGenerator().generate({}, original_filename='')
        fn = result['generated_filename']
        assert 'XXXX_(XXXX_XXXX_XXXX)_XX_XXXX_XXXX_XXXX_TO_XXXX.JPG' == fn

    def test_empty_enriched_none_filename(self):
        result = AMIFilenameGenerator().generate({})
        assert 'XXXX' in result['generated_filename']


# ---------------------------------------------------------------------------
# 4. Document type mapping
# ---------------------------------------------------------------------------

class TestDocumentTypeMapping:
    @pytest.mark.parametrize('doc_type,expected_code', [
        ('letter', 'LT'),
        ('book', 'BK'),
        ('notebook', 'NB'),
        ('diary', 'DY'),
        ('newsletter', 'NL'),
        ('transcript', 'TR'),
        ('magazine', 'MG'),
        ('newspaper', 'NP'),
        ('postcard', 'PC'),
        ('photograph', 'PH'),
        ('photo', 'PH'),
        ('audio', 'AU'),
        ('video', 'VD'),
        ('document', 'DC'),
        ('palm leaf manuscript', 'PM'),
        ('painting', 'PT'),
        ('memo', 'DC'),
        ('telegram', 'DC'),
        ('fax', 'DC'),
        ('email', 'DC'),
        ('invitation', 'DC'),
    ])
    def test_known_type(self, doc_type, expected_code):
        enriched = {'metadata': {'document_type': doc_type}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['document_type'] == expected_code

    def test_unknown_type_returns_XX(self):
        enriched = {'metadata': {'document_type': 'scroll'}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['document_type'] == 'XX'

    def test_case_insensitive_lookup(self):
        enriched = {'metadata': {'document_type': 'LETTER'}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['document_type'] == 'LT'

    def test_mixed_case_lookup(self):
        enriched = {'metadata': {'document_type': 'Letter'}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['document_type'] == 'LT'


# ---------------------------------------------------------------------------
# 5. Medium mapping
# ---------------------------------------------------------------------------

class TestMediumMapping:
    @pytest.mark.parametrize('medium,expected_code', [
        ('mixed', 'MIX'),
        ('pen', 'PEN'),
        ('pencil', 'PENCIL'),
        ('typewriter', 'TYPE'),
        ('typed', 'TYPE'),
        ('printed', 'PRINT'),
        ('handwritten', 'HAND'),
        ('handwriting', 'HAND'),
        ('carved', 'CARVE'),
        ('chalk', 'CHALK'),
        ('marker', 'MARKER'),
    ])
    def test_known_medium(self, medium, expected_code):
        enriched = {'document': {'physical_attributes': {'medium': medium}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['medium'] == expected_code

    def test_unknown_medium_returns_XXXX(self):
        enriched = {'document': {'physical_attributes': {'medium': 'crayon'}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['medium'] == 'XXXX'

    def test_case_insensitive_medium(self):
        enriched = {'document': {'physical_attributes': {'medium': 'Mixed'}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['medium'] == 'MIX'


# ---------------------------------------------------------------------------
# 6. Original filename parsing — AMI format
# ---------------------------------------------------------------------------

class TestAMIOriginalFilenameParsing:
    def test_extracts_master_id(self):
        result = AMIFilenameGenerator().generate({}, AMI_ORIGINAL)
        assert result['components']['master_identifier'] == AMI_MASTER_ID

    def test_extracts_sequence(self):
        result = AMIFilenameGenerator().generate({}, AMI_ORIGINAL)
        assert result['components']['sequence'] == AMI_SEQUENCE

    def test_ami_master_id_in_generated_filename(self):
        result = AMIFilenameGenerator().generate(make_enriched(), AMI_ORIGINAL)
        assert AMI_MASTER_ID in result['generated_filename']

    def test_ami_sequence_in_generated_filename(self):
        result = AMIFilenameGenerator().generate(make_enriched(), AMI_ORIGINAL)
        assert AMI_SEQUENCE in result['generated_filename']

    def test_different_sequence_numbers(self):
        fn = 'MSALTMEBA00200005.01_(03_04_0123)_LT_MIX_2000_JD_TO_RS.JPG'
        result = AMIFilenameGenerator().generate({}, fn)
        assert result['components']['master_identifier'] == 'MSALTMEBA00200005.01'
        assert result['components']['sequence'] == '(03_04_0123)'


# ---------------------------------------------------------------------------
# 7. Non-AMI original filename → XXXX fallbacks
# ---------------------------------------------------------------------------

class TestNonAMIOriginalFilename:
    def test_plain_filename_master_id_xxxx(self):
        result = AMIFilenameGenerator().generate(make_enriched(), 'scan001.jpg')
        assert result['components']['master_identifier'] == 'XXXX'

    def test_plain_filename_sequence_xxxx(self):
        result = AMIFilenameGenerator().generate(make_enriched(), 'scan001.jpg')
        assert result['components']['sequence'] == '(XXXX_XXXX_XXXX)'

    def test_no_extension_fallback(self):
        result = AMIFilenameGenerator().generate(make_enriched(), 'scan001')
        assert result['components']['extension'] == '.JPG'


# ---------------------------------------------------------------------------
# 8. Name formatting — Unicode, mixed case, extra spaces, numbers
# ---------------------------------------------------------------------------

class TestNameFormatting:
    def test_uppercase_ascii(self):
        enriched = make_enriched(sender='bk modi', recipient='revsngoenka')
        result = AMIFilenameGenerator().generate(enriched, AMI_ORIGINAL)
        assert result['components']['sender'] == 'BK MODI'
        assert result['components']['recipient'] == 'REVSNGOENKA'

    def test_extra_spaces_collapsed(self):
        enriched = make_enriched(sender='  BK   MODI  ')
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['sender'] == 'BK MODI'

    def test_unicode_name_upcase(self):
        # Devanagari characters — should pass through strip + upper (no change for non-ASCII)
        enriched = make_enriched(sender='राम', recipient='श्याम')
        result = AMIFilenameGenerator().generate(enriched)
        # Just verify no crash and names are present (uppercased)
        assert result['components']['sender'] != 'XXXX'
        assert result['components']['recipient'] != 'XXXX'

    def test_numbers_in_name(self):
        enriched = make_enriched(sender='MODI123')
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['sender'] == 'MODI123'

    def test_special_chars_stripped(self):
        enriched = make_enriched(sender='B.K. Modi')
        result = AMIFilenameGenerator().generate(enriched)
        # Dots stripped, spaces collapsed, uppercased
        assert result['components']['sender'] == 'BK MODI'

    def test_empty_name_fallback_xxxx(self):
        enriched = make_enriched(sender='   ')
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['sender'] == 'XXXX'


# ---------------------------------------------------------------------------
# 9. Extension handling
# ---------------------------------------------------------------------------

class TestExtensionHandling:
    @pytest.mark.parametrize('filename,expected_ext', [
        ('scan.jpg', '.JPG'),
        ('scan.JPG', '.JPG'),
        ('scan.png', '.PNG'),
        ('scan.tiff', '.TIFF'),
        ('scan.tif', '.TIF'),
        ('scan.pdf', '.PDF'),
        ('', '.JPG'),
        ('scan', '.JPG'),
    ])
    def test_extension(self, filename, expected_ext):
        result = AMIFilenameGenerator().generate({}, filename)
        assert result['components']['extension'] == expected_ext

    def test_extension_in_generated_filename(self):
        result = AMIFilenameGenerator().generate(make_enriched(), 'doc.png')
        assert result['generated_filename'].endswith('.PNG')


# ---------------------------------------------------------------------------
# 10. Year extraction
# ---------------------------------------------------------------------------

class TestYearExtraction:
    def test_from_temporal_markers(self):
        enriched = {'document': {'date': {'temporal_markers': {'year': '1990'}}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == '1990'

    def test_from_temporal_markers_int(self):
        enriched = {'document': {'date': {'temporal_markers': {'year': 2005}}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == '2005'

    def test_from_creation_date_iso(self):
        enriched = {'document': {'date': {'creation_date': '1985-06-15'}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == '1985'

    def test_from_sent_date_iso(self):
        enriched = {'document': {'date': {'sent_date': '2001-01-01'}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == '2001'

    def test_missing_year_returns_xxxx(self):
        enriched = {'document': {'date': {}}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == 'XXXX'

    def test_no_date_section_returns_xxxx(self):
        enriched = {'document': {}}
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == 'XXXX'

    def test_temporal_markers_takes_priority_over_creation_date(self):
        enriched = {
            'document': {
                'date': {
                    'temporal_markers': {'year': '1990'},
                    'creation_date': '2000-01-01',
                }
            }
        }
        result = AMIFilenameGenerator().generate(enriched)
        assert result['components']['year'] == '1990'


# ---------------------------------------------------------------------------
# 11. Component dict — all keys present
# ---------------------------------------------------------------------------

class TestComponentDict:
    EXPECTED_KEYS = {
        'master_identifier',
        'sequence',
        'document_type',
        'medium',
        'year',
        'sender',
        'recipient',
        'extension',
    }

    def test_all_component_keys_present_full(self):
        result = AMIFilenameGenerator().generate(make_enriched(), AMI_ORIGINAL)
        assert self.EXPECTED_KEYS == set(result['components'].keys())

    def test_all_component_keys_present_empty(self):
        result = AMIFilenameGenerator().generate({}, '')
        assert self.EXPECTED_KEYS == set(result['components'].keys())


# ---------------------------------------------------------------------------
# 12. Integration with bulk_processor result
# ---------------------------------------------------------------------------

class TestBulkProcessorIntegration:
    """
    Simulate what bulk_processor does: after enrichment, call generator and
    attach the result to the result dict.
    """

    def test_generated_filename_added_to_result(self):
        from app.services.ami_filename_generator import AMIFilenameGenerator

        enriched_data = make_enriched()
        filename = AMI_ORIGINAL

        result = {
            'enrichment': enriched_data,
        }

        gen = AMIFilenameGenerator()
        fname_result = gen.generate(enriched_data, filename)
        result['generated_filename'] = fname_result['generated_filename']
        result['generated_filename_components'] = fname_result['components']

        assert 'generated_filename' in result
        assert 'generated_filename_components' in result
        assert isinstance(result['generated_filename'], str)
        assert len(result['generated_filename']) > 0

    def test_generated_filename_not_empty(self):
        from app.services.ami_filename_generator import AMIFilenameGenerator

        gen = AMIFilenameGenerator()
        result = gen.generate(make_enriched(), AMI_ORIGINAL)
        assert result['generated_filename']

    def test_exception_in_generator_doesnt_break_caller(self):
        """Generator should not raise on malformed enriched_data."""
        gen = AMIFilenameGenerator()
        # Pass non-dict nested structures; should not raise
        malformed = {
            'metadata': None,
            'document': {'correspondence': None, 'physical_attributes': None, 'date': None},
        }
        result = gen.generate(malformed, '')
        assert 'generated_filename' in result


# ---------------------------------------------------------------------------
# 13. Integration with data_mapper merge_enriched_with_ocr
# ---------------------------------------------------------------------------

class TestDataMapperIntegration:
    """
    Verify that merge_enriched_with_ocr produces generated_filename fields.
    Requires a working DataMapper import.
    """

    def _make_minimal_ocr_data(self, filename='test.jpg'):
        return {
            'text': 'Hello world',
            'confidence': 0.95,
            'detected_language': 'en',
            'file_info': {'filename': filename},
            'metadata': {},
            'blocks': [],
            'words': [],
        }

    def test_merge_produces_generated_filename(self):
        try:
            from app.services.data_mapper import DataMapper
        except ImportError:
            pytest.skip("DataMapper not importable in this environment")

        ocr_data = self._make_minimal_ocr_data(AMI_ORIGINAL)
        enriched = make_enriched()

        merged = DataMapper.merge_enriched_with_ocr(
            ocr_data=ocr_data,
            enriched_data=enriched,
        )

        assert 'generated_filename' in merged
        assert 'generated_filename_components' in merged
        assert isinstance(merged['generated_filename'], str)

    def test_merge_generated_filename_not_empty(self):
        try:
            from app.services.data_mapper import DataMapper
        except ImportError:
            pytest.skip("DataMapper not importable in this environment")

        ocr_data = self._make_minimal_ocr_data(AMI_ORIGINAL)
        merged = DataMapper.merge_enriched_with_ocr(
            ocr_data=ocr_data,
            enriched_data=make_enriched(),
        )
        assert merged['generated_filename']

    def test_merge_ami_original_preserves_master_id(self):
        try:
            from app.services.data_mapper import DataMapper
        except ImportError:
            pytest.skip("DataMapper not importable in this environment")

        ocr_data = self._make_minimal_ocr_data(AMI_ORIGINAL)
        merged = DataMapper.merge_enriched_with_ocr(
            ocr_data=ocr_data,
            enriched_data=make_enriched(),
        )
        assert AMI_MASTER_ID in merged['generated_filename']
