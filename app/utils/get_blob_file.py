from google.cloud.storage import Blob
from google.genai.types import Part
from mimetypes import guess_type
from app.utils.file import PartFile


def get_file_from_storage(blob: Blob) -> PartFile:
    """
    This function downloads a blob from gcp and transforms it into a utility partfile
    dataclass so it can be sent directly for the genai api and hold metadata util in the context
    of this app
    """
    file_bytes = blob.download_as_bytes()
    parts = blob.name.split('/', 2)[1:]  # remove the origin folder and split the path
    if len(parts) == 2:
        # means the file has a 'folder'. In the context of the app the file was inside a zip
        parent, filename = parts
    else:
        # if not then the file was a single file
        parent, filename = None, parts[0]

    # GCP bucket sometimes sets a wrong mimetype for pdfs (octet-stream) which is not supported by genai library
    part = Part.from_bytes(data=file_bytes, mime_type=guess_type(filename)[0])
    return PartFile(
        part=part,
        path=f"gs://{blob.bucket.name}/{blob.name}",
        original_filename=filename,
        parent_file=f"{parent}.zip" if parent else None
    )
