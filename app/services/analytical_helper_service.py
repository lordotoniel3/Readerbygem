from typing import Dict, Any

from app.utils.file import PartFile
import logging
logger = logging.getLogger("uvicorn.error")

class AnalyticalHelperService:
    """
    A service to assist with analytical tasks such as extracting date from document names.
    """

    @staticmethod
    def extract_date_from_filename(file: PartFile) -> Dict[str, Any]:
        """
        Extracts a date from the first 8 characters of the filename in 'YYYYMMDD' format.

        Args:
            file (PartFile): The file object containing the filename.

        Returns:
            str or None: The extracted date in 'YYYY-MM-DD' format, or None if extraction fails.
        """
        try:
            filename: str = file.original_filename
            
            # Check if filename has at least 8 characters
            if len(filename) < 8:
                logger.warning(f"Filename '{filename}' has less than 8 characters, cannot extract date")
                return None
                
            # Extract the first 8 characters from the filename
            date_str = filename[:8]
            
            # Validate that the first 8 characters are numeric (basic date validation)
            if not date_str.isdigit():
                logger.warning(f"First 8 characters '{date_str}' of filename '{filename}' are not numeric")
                return None

            # Cast the string into a date object
            date = date_str[:4] + '-' + date_str[4:6] + '-' + date_str[6:8]
            return date
        except Exception as e:
            # Get filename safely for error logging
            filename_for_error = getattr(file, 'original_filename', 'unknown')
            # Log the error with the filename
            logger.error(f"Error extracting date from filename '{filename_for_error}': {e}")
            return None
