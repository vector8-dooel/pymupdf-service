import uuid
import fitz
from concurrent.futures import ProcessPoolExecutor
import os
import logging
from typing import Tuple, List, Optional
from enum import Enum

# Set environment variable to disable tokenizers parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class CategoryEnum(str, Enum):
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    LIST_ITEM = "list_item"
    PAGE_FOOTER = "page_footer"
    PAGE_HEADER = "page_header"
    PICTURE = "picture"
    SECTION_HEADER = "section_header"
    TABLE = "table"
    TEXT = "text"
    TITLE = "title"
    DOCUMENT_INDEX = "document_index"
    CODE = "code"
    CHECKBOX_SELECTED = "checkbox_selected"
    CHECKBOX_UNSELECTED = "checkbox_unselected"
    FORM = "form"
    KEY_VALUE_REGION = "key_value_region"
    PARAGRAPH = "paragraph"
    REFERENCE = "reference"
    IMAGE = "image"

    def __str__(self):
        return str(self.value)

class Element:
    def __init__(
        self,
        text: str,
        category: Optional[CategoryEnum] = None,
        start_page: Optional[int] = 1,
        end_page: Optional[int] = 1,
        b64: Optional[str] = None
    ):
        self.text = text
        self.category = category
        self.start_page = start_page
        self.end_page = end_page
        self.b64 = b64


class PymupdfParser:
    """
    A parser for extracting structured elements such as text and tables from PDFs using PyMuPDF.

    Attributes:
        max_processors (int): Maximum number of processors to utilize.
        footer_margin (int): Margin from the bottom of the page to ignore as footer.
        header_margin (int): Margin from the top of the page to ignore as header.
        no_image_text (bool): Whether to exclude text overlaid on images.
        tolerance (int): Tolerance for merging table bounding boxes.
    """

    def __init__(
        self,
        max_processors: int,
        footer_margin: int,
        header_margin: int,
        no_image_text: bool,
        tolerance: int,
    ):
        super().__init__()
        self.max_processors = max_processors
        self.footer_margin = footer_margin
        self.header_margin = header_margin
        self.no_image_text = no_image_text
        self.tolerance = tolerance

    def parse(
        self, file: bytes, session_id: Optional[uuid.UUID] = None
    ) -> Tuple[list[Element], int]:
        """
        Parse a PDF file and extract elements such as text and tables.

        Args:
            file (bytes): Byte content of the PDF file to parse.
            session_id (Optional[uuid.UUID]): Optional session identifier.

        Returns:
            Tuple[list[Element], int]: A list of parsed elements containing content and metadata,
                                      and the number of pages in the document.
        """
        try:
            # Open the document directly from memory
            doc = fitz.open(stream=file, filetype="pdf")
            num_pages = len(doc)

            page_segments = self.get_page_segments(num_pages)
            num_utilized_processors = len(page_segments)

            logging.info(f"Processing PDF using {num_utilized_processors} processors")

            # Create arguments for each worker
            chunk_args = [
                (file, start_page, end_page) for start_page, end_page in page_segments
            ]

            # Process pages in parallel
            with ProcessPoolExecutor(max_workers=num_utilized_processors) as executor:
                chunk_results = list(executor.map(self.process_page_chunk, chunk_args))
                results = [result for chunk in chunk_results for result in chunk]

            # Sort results by page number
            results.sort(key=lambda x: x[0])

            # Convert results to Element objects
            elements = [
                Element(
                    self.extract_bbox_text(doc[page_num], bbox),
                    content_type,
                    page_num + 1,
                    page_num + 1,
                )
                for page_num, content in results
                for bbox, content_type in content
            ]

            doc.close()
            return elements, num_pages

        except Exception as e:
            logging.error(
                f"Unexpected error during PDF parsing: {str(e)}", exc_info=True
            )
            raise

    def get_page_segments(self, num_pages: int) -> List[Tuple[int, int]]:
        """
        Divide pages into segments for parallel processing.

        Args:
            num_pages (int): Total number of pages in the document.

        Returns:
            List[Tuple[int, int]]: List of tuples where each tuple defines a start and end page range.

        Raises:
            ValueError: If max_processors is less than or equal to 0.
        """
        if self.max_processors <= 0:
            raise ValueError("Number of processors must be greater than 0")

        chunk_size = num_pages // self.max_processors
        remainder = num_pages % self.max_processors

        chunks = []
        start_page = 0

        for i in range(self.max_processors):
            extra = 1 if i < remainder else 0
            end_page = start_page + chunk_size + extra
            end_page = min(end_page, num_pages)
            chunks.append((start_page, end_page))
            start_page = end_page

            if start_page >= num_pages:
                break

        return chunks

    def process_page_chunk(self, args: Tuple[bytes, int, int]) -> List[Tuple[int, list]]:
        """
        Process a chunk of pages and extract their content.

        Args:
            args (Tuple[bytes, int, int]): Tuple containing file bytes, start page, and end page.

        Returns:
            List[Tuple[int, list]]: List of page numbers and their extracted content.
        """
        file_bytes, start_page, end_page = args

        results = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_num in range(start_page, end_page):
            page = doc[page_num]
            page.wrap_contents()
            content = self.get_ordered_content(page)
            results.append((page_num, content))

        doc.close()

        return results

    def get_ordered_content(self, page) -> List:
        """
        Extract and order content from a page, distinguishing between text and tables.

        Args:
            page (fitz.Page): The page to extract content from.

        Returns:
            List: Ordered content as bounding boxes with their associated types (text or table).
        """
        text_bboxes = self.column_boxes(page)

        tables = page.find_tables()
        table_bboxes = [fitz.IRect(table.bbox) for table in tables]
        merged_tables = self.merge_tables(table_bboxes)

        ordered_content = []
        processed_tables = set()

        for text_bbox in text_bboxes:
            intersecting_tables = []

            for table_bbox in merged_tables:
                if not (text_bbox & table_bbox).is_empty:
                    intersecting_tables.append(table_bbox)

            if not intersecting_tables:
                ordered_content.append((text_bbox, "text"))
                continue

            intersecting_tables.sort(key=lambda x: x.y0)

            bbox_above, bbox_below = self.split_bbox_by_table(
                text_bbox, intersecting_tables[0], page
            )

            if bbox_above:
                ordered_content.append((bbox_above, "text"))

            table_key = (
                intersecting_tables[0].x0,
                intersecting_tables[0].y0,
                intersecting_tables[0].x1,
                intersecting_tables[0].y1,
            )
            if table_key not in processed_tables:
                ordered_content.append((intersecting_tables[0], "table"))
                processed_tables.add(table_key)

            current_bbox = bbox_below
            for table_bbox in intersecting_tables[1:]:
                if current_bbox:
                    bbox_above, bbox_below = self.split_bbox_by_table(
                        current_bbox, table_bbox, page
                    )
                    if bbox_above:
                        ordered_content.append((bbox_above, "text"))

                    table_key = (
                        table_bbox.x0,
                        table_bbox.y0,
                        table_bbox.x1,
                        table_bbox.y1,
                    )
                    if table_key not in processed_tables:
                        ordered_content.append((table_bbox, "table"))
                        processed_tables.add(table_key)

                    current_bbox = bbox_below

            if current_bbox:
                ordered_content.append((current_bbox, "text"))
        return ordered_content

    def column_boxes(self, page):
        """
        Extract column bounding boxes from a page.
        Handles edge cases where blocks have no lines or invalid bounding boxes.

        Args:
            page (fitz.Page): The page to analyze for column structure.

        Returns:
            List[fitz.IRect]: List of column bounding boxes.
        """
        # [Rest of the column_boxes method remains unchanged]
        paths = page.get_drawings()
        bboxes = []
        path_rects = []
        img_bboxes = []
        vert_bboxes = []

        clip = +page.rect
        clip.y1 -= self.footer_margin
        clip.y0 += self.header_margin

        def can_extend(temp, bb, bboxlist):
            for b in bboxlist:
                if not intersects_bboxes(temp, vert_bboxes) and (
                    b is None or b == bb or (temp & b).is_empty
                ):
                    continue
                return False
            return True

        def in_bbox(bb, bboxes):
            for i, bbox in enumerate(bboxes):
                if bb in bbox:
                    return i + 1
            return 0

        def intersects_bboxes(bb, bboxes):
            for bbox in bboxes:
                if not (bb & bbox).is_empty:
                    return True
            return False

        def extend_right(bboxes, width, path_bboxes, vert_bboxes, img_bboxes):
            for i, bb in enumerate(bboxes):
                if in_bbox(bb, path_bboxes):
                    continue

                if in_bbox(bb, img_bboxes):
                    continue

                temp = +bb
                temp.x1 = width

                if intersects_bboxes(temp, path_bboxes + vert_bboxes + img_bboxes):
                    continue

                check = can_extend(temp, bb, bboxes)
                if check:
                    bboxes[i] = temp

            return [b for b in bboxes if b is not None]

        def clean_nblocks(nblocks):
            blen = len(nblocks)
            if blen < 2:
                return nblocks
            start = blen - 1
            for i in range(start, -1, -1):
                bb1 = nblocks[i]
                bb0 = nblocks[i - 1]
                if bb0 == bb1:
                    del nblocks[i]

            y1 = nblocks[0].y1
            i0 = 0
            i1 = -1

            for i in range(1, len(nblocks)):
                b1 = nblocks[i]
                if abs(b1.y1 - y1) > 10:
                    if i1 > i0:
                        nblocks[i0 : i1 + 1] = sorted(
                            nblocks[i0 : i1 + 1], key=lambda b: b.x0
                        )
                    y1 = b1.y1
                    i0 = i
                i1 = i
            if i1 > i0:
                nblocks[i0 : i1 + 1] = sorted(nblocks[i0 : i1 + 1], key=lambda b: b.x0)
            return nblocks

        # Check if structured extraction is possible
        try:
            # Extract paths and images first
            for p in paths:
                path_rects.append(p["rect"].irect)
            path_bboxes = path_rects

            path_bboxes.sort(key=lambda b: (b.y0, b.x0))
            for item in page.get_images():
                img_bboxes.extend(page.get_image_rects(item[0]))

            # Get the blocks using default dictionary method
            blocks = page.get_text(
                "dict",
                flags=fitz.TEXTFLAGS_TEXT,
                clip=clip,
            )["blocks"]

            # If blocks is empty or contains invalid blocks, fall back to simple extraction
            if not blocks:
                logging.warning(
                    f"No blocks found on page {page.number}, falling back to simple text extraction"
                )
                return [clip]

            # Check if any block has invalid bounding box coordinates
            has_invalid_blocks = False
            for b in blocks:
                bbox_coords = b.get("bbox", (0, 0, 0, 0))
                # Check for extreme values that indicate invalid bounding boxes
                if any(coord > 2147483000 for coord in bbox_coords) or any(
                    coord < -2147483000 for coord in bbox_coords
                ):
                    has_invalid_blocks = True
                    logging.warning(f"Invalid block bbox found: {bbox_coords}")
                    break

            if has_invalid_blocks:
                logging.warning(
                    f"Invalid blocks found on page {page.number}, falling back to simple text extraction"
                )
                return [clip]

            # Process valid blocks
            for b in blocks:
                bbox = fitz.IRect(b["bbox"])

                if self.no_image_text and in_bbox(bbox, img_bboxes):
                    continue

                # Check if 'lines' key exists and is not empty
                if "lines" not in b or not b["lines"]:
                    continue  # Skip this block and move to the next one

                try:
                    line0 = b["lines"][0]
                    if line0["dir"] != (1, 0):  # Check direction
                        vert_bboxes.append(bbox)
                        continue
                except (IndexError, KeyError, TypeError):
                    continue  # Skip problematic blocks

                # Process lines in the block
                srect = fitz.EMPTY_IRECT()
                for line in b["lines"]:
                    try:
                        lbbox = fitz.IRect(line["bbox"])
                        text = "".join([s["text"].strip() for s in line["spans"]])
                        if len(text) > 1:
                            srect |= lbbox
                    except (KeyError, TypeError):
                        continue  # Skip problematic lines

                bbox = +srect

                if not bbox.is_empty:
                    bboxes.append(bbox)

            # Handle the case where no valid bboxes were found
            if not bboxes:
                logging.warning(
                    f"No valid bboxes found on page {page.number}, falling back to simple text extraction"
                )
                return [clip]  # Return the entire page as one bbox

            # Continue with normal processing for valid bboxes
            bboxes.sort(key=lambda k: (in_bbox(k, path_bboxes), k.y0, k.x0))
            bboxes = extend_right(
                bboxes, int(page.rect.width), path_bboxes, vert_bboxes, img_bboxes
            )

            if not bboxes:
                return [clip]

            nblocks = [bboxes[0]]
            bboxes = bboxes[1:]

            for i, bb in enumerate(bboxes):
                check = False

                for j in range(len(nblocks)):
                    nbb = nblocks[j]

                    if bb is None or nbb.x1 < bb.x0 or bb.x1 < nbb.x0:
                        continue

                    if in_bbox(nbb, path_bboxes) != in_bbox(bb, path_bboxes):
                        continue

                    temp = bb | nbb
                    check = can_extend(temp, nbb, nblocks)
                    if check:
                        break

                if not check:
                    nblocks.append(bb)
                    j = len(nblocks) - 1
                    temp = nblocks[j]

                check = can_extend(temp, bb, bboxes)
                if not check:
                    nblocks.append(bb)
                else:
                    nblocks[j] = temp
                bboxes[i] = None

            nblocks = clean_nblocks(nblocks)
            return nblocks

        except Exception as e:
            # If any error occurs during structured extraction, fall back to simple extraction
            logging.error(
                f"Error in column_boxes: {str(e)}, falling back to simple text extraction"
            )
            return [clip]

    def split_bbox_by_table(self, text_bbox, table_bbox, page):
        """
        Split a text bounding box by intersecting table bounding boxes.

        Args:
            text_bbox (fitz.IRect): Text bounding box to split.
            table_bbox (fitz.IRect): Table bounding box causing the split.
            page (fitz.Page): The page containing the bounding boxes.

        Returns:
            Tuple[Optional[fitz.IRect], Optional[fitz.IRect]]: Bounding boxes above and below the table.
        """
        bbox_above = None
        bbox_below = None

        if text_bbox.y0 < table_bbox.y0:
            potential_bbox_above = fitz.IRect(
                text_bbox.x0, text_bbox.y0, text_bbox.x1, table_bbox.y0
            )
            text_above = page.get_text("text", clip=potential_bbox_above).strip()
            if text_above:
                bbox_above = potential_bbox_above

        if text_bbox.y1 > table_bbox.y1:
            potential_bbox_below = fitz.IRect(
                text_bbox.x0, table_bbox.y1, text_bbox.x1, text_bbox.y1
            )
            text_below = page.get_text("text", clip=potential_bbox_below).strip()
            if text_below:
                bbox_below = potential_bbox_below

        return bbox_above, bbox_below

    def merge_tables(self, table_bboxes):
        """
        Merge overlapping or closely aligned table bounding boxes.

        Args:
            table_bboxes (List[fitz.IRect]): List of table bounding boxes to merge.

        Returns:
            List[fitz.IRect]: Merged table bounding boxes.
        """
        if not table_bboxes:
            return []

        merged = []
        current_group = table_bboxes[0]

        for bbox in table_bboxes[1:]:
            if self.should_merge_tables(current_group, bbox):
                current_group = fitz.IRect(
                    min(current_group.x0, bbox.x0),
                    min(current_group.y0, bbox.y0),
                    max(current_group.x1, bbox.x1),
                    max(current_group.y1, bbox.y1),
                )
            else:
                merged.append(current_group)
                current_group = bbox

        merged.append(current_group)
        return merged

    def should_merge_tables(self, bbox1, bbox2):
        """
        Determine whether two table bounding boxes should be merged based on alignment and proximity.

        Args:
            bbox1 (fitz.IRect): First bounding box.
            bbox2 (fitz.IRect): Second bounding box.

        Returns:
            bool: True if the bounding boxes should be merged, otherwise False.
        """
        horizontally_aligned = (
            abs(bbox1.y0 - bbox2.y0) < self.tolerance
            and abs(bbox1.y1 - bbox2.y1) < self.tolerance
        )
        vertically_aligned = (
            abs(bbox1.x0 - bbox2.x0) < self.tolerance
            and abs(bbox1.x1 - bbox2.x1) < self.tolerance
        )

        horizontal_distance = min(abs(bbox1.x1 - bbox2.x0), abs(bbox2.x1 - bbox1.x0))
        vertical_distance = min(abs(bbox1.y1 - bbox2.y0), abs(bbox2.y1 - bbox1.y0))

        is_close = (
            horizontal_distance < self.tolerance or vertical_distance < self.tolerance
        )

        return (horizontally_aligned or vertically_aligned) and is_close

    def extract_bbox_text(self, page, bbox):
        """
        Extract text from a specific bounding box on a page.

        Args:
            page (fitz.Page): The page containing the bounding box.
            bbox (fitz.IRect): The bounding box from which to extract text.

        Returns:
            str: Extracted text.
        """
        return page.get_text("text", clip=bbox).strip()