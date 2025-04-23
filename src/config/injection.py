from pathlib import Path

import yaml
from dependency_injector import containers, providers


from src.services.pdf_service import PDFParseService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src"])

    parser_settings_path = Path("src/config/parser_settings.yaml")
    with open(parser_settings_path, "r") as f:
        parser_settings = yaml.safe_load(f)

    pdf_parse_service = providers.Singleton(
        PDFParseService,
        config=parser_settings,
    )
