import asyncio
from concurrent.futures import ProcessPoolExecutor

import pytest
from unittest.mock import MagicMock, patch, ANY
import fitz

from src.parser_lib.pdf_parser import PymupdfParser


@pytest.fixture
def default_parser():
    """Fixture for creating a default PymupdfParser instance."""
    return PymupdfParser(
        max_processors=4,
        footer_margin=0,
        header_margin=0,
        no_image_text=False,
        tolerance=20,
    )


@pytest.mark.parametrize(
    "num_pages, max_processors, expected_segments",
    [
        (10, 4, [(0, 3), (3, 6), (6, 8), (8, 10)]),  # Case with exact page splits
        (5, 3, [(0, 2), (2, 4), (4, 5)]),  # Case with fewer pages than processors
        (0, 2, [(0, 0)]),  # Edge case: no pages
        (5, 10, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]),  # More processors than pages
        (5, 0, []),  # Case with 0 processors
    ],
)
def test_get_page_segments(num_pages, max_processors, expected_segments):
    """Test page segmentation logic with varying input."""
    if max_processors == 0:  # Handle edge case where processors are 0
        with pytest.raises(
            ValueError, match="Number of processors must be greater than 0"
        ):
            parser = PymupdfParser(
                max_processors=max_processors,
                footer_margin=0,
                header_margin=0,
                no_image_text=False,
                tolerance=20,
            )
            parser.get_page_segments(num_pages)
    else:
        parser = PymupdfParser(
            max_processors=max_processors,
            footer_margin=0,
            header_margin=0,
            no_image_text=False,
            tolerance=20,
        )
        segments = parser.get_page_segments(num_pages)
        assert segments == expected_segments


@patch("fitz.open")
def test_process_page_chunk(mock_fitz_open, default_parser):
    """Test processing a chunk of pages."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 5
    mock_fitz_open.return_value = mock_doc

    mock_page.wrap_contents = MagicMock()
    default_parser.get_ordered_content = MagicMock(return_value=[(("bbox"), "text")])

    file_bytes = b"dummy"
    results = default_parser.process_page_chunk(
        file_bytes,
        0,
        3,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
        default_parser.tolerance,
    )
    assert len(results) == 3
    default_parser.get_ordered_content.assert_called()


@pytest.mark.parametrize(
    "bboxes, expected_len",
    [
        (
            [
                {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
                {"x0": 9, "y0": 9, "x1": 20, "y1": 20},
                {"x0": 50, "y0": 50, "x1": 60, "y1": 60},
            ],
            2,
        ),
        (
            [
                {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
                {"x0": 20, "y0": 20, "x1": 30, "y1": 30},
            ],
            2,
        ),
    ],
)
def test_merge_tables(default_parser, bboxes, expected_len):
    """Test merging of table bounding boxes."""
    # Mock the bounding boxes
    bboxes_mock = [MagicMock(**bbox) for bbox in bboxes]

    merged_tables = default_parser.merge_tables(bboxes_mock, default_parser.tolerance)
    assert len(merged_tables) == expected_len


@pytest.fixture
def sample_pdf_bytes():
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 21>>stream\nBT\n/F1 12 Tf\n(Test) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n0000000192 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n264\n%%EOF"
    )


def test_parse_with_sample_pdf(sample_pdf_bytes):
    parser = PymupdfParser(
        max_processors=2,
        footer_margin=10,
        header_margin=10,
        no_image_text=False,
        tolerance=20,
    )
    with patch("fitz.open", return_value=MagicMock(spec=fitz.Document)):
        with ProcessPoolExecutor() as executor:
            result = asyncio.run(parser.parse(sample_pdf_bytes, executor))
            assert result is not None


@pytest.mark.parametrize(
    "bbox1, bbox2, expected_result",
    [
        (
            {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
            {"x0": 9, "y0": 9, "x1": 20, "y1": 20},
            True,
        ),  # Overlapping bounding boxes
        (
            {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
            {"x0": 50, "y0": 50, "x1": 60, "y1": 60},
            False,
        ),  # Non-overlapping bounding boxes
    ],
)
def test_should_merge_tables(default_parser, bbox1, bbox2, expected_result):
    """Test the logic to decide if two tables should merge."""
    bbox1_mock = MagicMock(**bbox1)
    bbox2_mock = MagicMock(**bbox2)

    result = default_parser.should_merge_tables(
        bbox1_mock, bbox2_mock, default_parser.tolerance
    )
    assert result is expected_result


@patch("fitz.Page")
def test_extract_bbox_text(mock_page, default_parser):
    """Test extraction of text from bounding boxes."""
    mock_page.get_text.return_value = "sample text"
    bbox = MagicMock()
    result = default_parser.extract_bbox_text(mock_page, bbox)
    assert result == "sample text"


def test_split_bbox_by_table(default_parser):
    """Test splitting a text bounding box by table bounding boxes."""
    page = MagicMock()
    bbox = MagicMock(x0=0, y0=0, x1=10, y1=20)
    table_bbox = MagicMock(x0=0, y0=10, x1=10, y1=15)

    page.get_text.side_effect = ["text above", "text below"]
    bbox_above, bbox_below = default_parser.split_bbox_by_table(bbox, table_bbox, page)
    assert bbox_above is not None
    assert bbox_below is not None


def test_get_page_segments_edge_case(default_parser):
    """Test page segmentation with fewer pages than processors."""
    num_pages = 2
    segments = default_parser.get_page_segments(num_pages)
    assert len(segments) == 2
    assert segments == [(0, 1), (1, 2)]


def test_parse_large_pdf(default_parser):
    large_pdf_bytes = b"%PDF-1.4\n" + b"0" * (6 * 1024 * 1024)  # 6 MB PDF
    with patch("fitz.open", return_value=MagicMock(spec=fitz.Document)):
        with ProcessPoolExecutor() as executor:
            result = asyncio.run(default_parser.parse(large_pdf_bytes, executor))
            assert result is not None


def test_parse_small_pdf(default_parser):
    small_pdf_bytes = b"%PDF-1.4\n" + b"0" * (1 * 1024 * 1024)  # 1 MB PDF
    with patch("fitz.open", return_value=MagicMock(spec=fitz.Document)):
        with ProcessPoolExecutor() as executor:
            result = asyncio.run(default_parser.parse(small_pdf_bytes, executor))
            assert result is not None


def test_parse_corrupted_pdf(default_parser):
    corrupted_pdf_bytes = b"%PDF-1.4\ncorrupted content"
    with patch("fitz.open", side_effect=RuntimeError("Corrupted PDF")):
        with ProcessPoolExecutor() as executor:
            with pytest.raises(RuntimeError, match="Corrupted PDF"):
                asyncio.run(default_parser.parse(corrupted_pdf_bytes, executor))


def test_get_ordered_content_text_only(default_parser):
    """Test get_ordered_content with pages containing only text."""
    mock_page = MagicMock()
    mock_page.find_tables.return_value = []
    mock_page.get_text.return_value = "sample text"
    result = default_parser.get_ordered_content(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
        default_parser.tolerance,
    )
    assert result == [(ANY, "text")]


def test_get_ordered_content_tables_only(default_parser):
    """Test get_ordered_content with pages containing only tables."""
    mock_page = MagicMock()

    mock_table = MagicMock()
    mock_table.bbox = (0, 0, 10, 10)
    mock_page.find_tables.return_value = [mock_table]

    text_bbox = fitz.IRect(0, 0, 10, 10)
    default_parser.column_boxes = MagicMock(return_value=[text_bbox])

    default_parser.extract_bbox_text = MagicMock(return_value="")
    default_parser.split_bbox_by_table = MagicMock(return_value=(None, None))

    result = default_parser.get_ordered_content(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
        default_parser.tolerance,
    )

    assert len(result) == 1
    assert result[0][1] == "table"


def test_get_ordered_content_text_and_tables(default_parser):
    """Test get_ordered_content with pages containing both text and tables."""
    mock_page = MagicMock()

    mock_table = MagicMock()
    mock_table.bbox = (0, 0, 10, 10)
    mock_page.find_tables.return_value = [mock_table]

    text_bbox = fitz.IRect(0, 0, 100, 100)
    default_parser.column_boxes = MagicMock(return_value=[text_bbox])

    default_parser.extract_bbox_text = MagicMock(return_value="sample text")

    result = default_parser.get_ordered_content(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
        default_parser.tolerance,
    )

    assert len(result) > 0
    assert any(item[1] == "text" for item in result)
    assert any(item[1] == "table" for item in result)


def test_column_boxes_varied_structure(default_parser):
    """Test column_boxes with pages having different column structures."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [{"bbox": (0, 0, 10, 10), "lines": [{"dir": (1, 0)}]}]
    }
    result = default_parser.column_boxes(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
    )
    assert len(result) > 0


def test_column_boxes_no_valid_blocks(default_parser):
    """Test column_boxes with pages having no valid blocks."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {"blocks": []}
    result = default_parser.column_boxes(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
    )
    assert result == [ANY]


def test_split_bbox_by_table_no_intersection(default_parser):
    page = MagicMock()
    bbox = MagicMock(x0=0, y0=0, x1=10, y1=10)
    table_bbox = MagicMock(x0=0, y0=20, x1=10, y1=30)  # No vertical overlap
    page.get_text.return_value = ""
    bbox_above, bbox_below = default_parser.split_bbox_by_table(bbox, table_bbox, page)
    assert bbox_above is None
    assert bbox_below is None


@patch("fitz.open")
def test_parse_cleanup_on_exception(mock_fitz_open):
    """Test file cleanup in finally block when exception occurs."""
    mock_fitz_open.side_effect = Exception("Test exception")

    parser = PymupdfParser(
        max_processors=2,
        footer_margin=10,
        header_margin=10,
        no_image_text=False,
        tolerance=20,
    )

    with pytest.raises(Exception):
        parser.parse(b"%PDF-1.4\n")


def test_column_boxes_with_invalid_block_data(default_parser):
    """Test column_boxes with blocks containing invalid data structures."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {"bbox": (0, 0, 10, 10), "lines": []},
            {"bbox": (20, 20, 30, 30)},
            {
                "bbox": (40, 40, 50, 50),
                "lines": [{"missing_dir": True}],
            },
            {
                "bbox": (2147483647, 0, 10, 10),
                "lines": [{"dir": (1, 0)}],
            },
        ]
    }

    mock_page.rect = MagicMock()
    mock_page.rect.width = 100

    result = default_parser.column_boxes(
        mock_page,
        default_parser.footer_margin,
        default_parser.header_margin,
        default_parser.no_image_text,
    )
    assert result is not None


@patch("fitz.open")
def test_process_page_chunk_exception(mock_fitz_open, default_parser):
    """Test process_page_chunk handling exceptions."""
    mock_doc = MagicMock()
    mock_doc.__getitem__.side_effect = Exception("Document processing error")
    mock_fitz_open.return_value = mock_doc

    with pytest.raises(Exception):
        default_parser.process_page_chunk(
            b"dummy",
            0,
            3,
            default_parser.footer_margin,
            default_parser.header_margin,
            default_parser.no_image_text,
            default_parser.tolerance,
        )


def test_merge_tables_empty_input(default_parser):
    """Test merge_tables with empty input."""
    result = default_parser.merge_tables([], default_parser.tolerance)
    assert result == []


def test_merge_tables_single_input(default_parser):
    """Test merge_tables with single table bbox."""
    bbox = MagicMock(x0=0, y0=0, x1=10, y1=10)
    result = default_parser.merge_tables([bbox], default_parser.tolerance)
    assert len(result) == 1
    assert result[0] == bbox


@patch("fitz.Page")
def test_extract_bbox_text_empty(mock_page, default_parser):
    """Test extraction of empty text from bounding boxes."""
    mock_page.get_text.return_value = ""
    bbox = MagicMock()
    result = default_parser.extract_bbox_text(mock_page, bbox)
    assert result == ""
