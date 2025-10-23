from typing import Optional

from google.genai.types import Part
from pydantic import BaseModel

class PartFile(BaseModel):
    """
    This is a utility dataclass to hold a genai Part to make gemini calls from memory
    and some extra metadata extracted from the blob for internal use
    """
    part: Part
    path: str # gs path eg gs://bucket/folder/file.pdf
    original_filename: str #file.pdf
    parent_file: Optional[str] #parent file of the app, in this context the file was inside a zip then eg: archive.zip