from pathlib import PurePath
from typing import Any

from PIL import Image


def convert_from_bytes(
    pdf_file: bytes,
    dpi: int = 200,
    output_folder: str | PurePath | None = None,
    first_page: int | None = None,
    last_page: int | None = None,
    fmt: str = "ppm",
    jpegopt: dict[Any, Any] | None = None,
    thread_count: int = 1,
    userpw: str | None = None,
    ownerpw: str | None = None,
    use_cropbox: bool = False,
    strict: bool = False,
    transparent: bool = False,
    single_file: bool = False,
    output_file: str | PurePath = ...,
    poppler_path: str | PurePath | None = None,
    grayscale: bool = False,
    size: tuple[int, ...] | int | None = None,
    paths_only: bool = False,
    use_pdftocairo: bool = False,
    timeout: int | None = None,
    hide_annotations: bool = False,
) -> list[Image.Image]:
    ...
