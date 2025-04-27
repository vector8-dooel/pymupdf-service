# pymupdf-service

A FastAPI microservice for parsing PDF files into structured text and tables using PyMuPDF.

## Features
- **Concurrent PDF parsing** with configurable number of workers via `ProcessPoolExecutor`.
- **Customizable margins** (`footer_margin`, `header_margin`), **image-text filtering** (`no_image_text`), and **table merge tolerance**.
- **Thin wrapper service** (`PDFParseService`) to construct and reuse a single parser instance.
- **REST API** endpoint for uploading PDFs and returning JSON-serialized elements.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/pymupdf-service.git
   cd pymupdf-service
   ```
2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

## Configuration
Service-level defaults are defined in ([parser_settings.yaml](src/config/parser_settings.yaml)):
- `max_processors`: Number of parallel workers (default: 2)
- `footer_margin`: Bottom margin to ignore as footer (default: 10)
- `header_margin`: Top margin to ignore as header (default: 10)
- `no_image_text`: Exclude text over images if `true` (default: `false`)
- `tolerance`: Pixel tolerance for merging adjacent table bounding boxes (default: 20)

## Running the Service with docker
Start the FastAPI server:
```bash
docker build -t pymupdf-service . 
docker run -p 8888:8888 pymupdf-service
```

## API Usage
### POST `/v1/pdf/parse`
Form-data parameters:
- `file`: PDF file to parse (`UploadFile`, required)
- `footer_margin`: Optional integer
- `header_margin`: Optional integer
- `no_image_text`: Optional boolean
- `tolerance`: Optional integer

**Response**
```json
{
  "elements": [
    {
      "content": "Extracted text or table snippet...",
      "content_type": "text|table",
      "start_page": 1,
      "end_page": 1
    }
  ],
  "num_pages": 5
}
```

## Contributing
1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## License
AGPL-3.0 © Vector8

