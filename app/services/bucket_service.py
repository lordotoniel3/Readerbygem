import io
import logging
import zipfile
from pathlib import PurePosixPath
from google.cloud import storage
from google.api_core.exceptions import NotFound, Forbidden
from google.cloud.storage import Blob

logger = logging.getLogger("uvicorn.error")
# WARNING: THIS IS JUST A FAILSAFE TO AVOID DOING MUCH WORK PER SIMPLE REQUEST OR BATCH
# THE ARCHITECTURE RIGHT NOW IS NOT ROBUST ENOUGH TO SUPPORT A FAILOVER OR A SERVICE FAIL
# THE IDEA IS TO IMPLEMENT A BROKER WITH AN EVENT ORIENTED ARCHITECTURE, THIS WILL ALLOW US
# TO HANDLE RETRIES, BETTER ERROR HANDLING AND THE MOST IMPORTANT THING THAT IS RESUME A PROCESS
# IF IT IS NOT ENDED
MAX_FILE_PROCESSING = 300

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024  # 500 MB
MAX_FILES = 200  # MAX ZIP FILES


def get_bucket_service():
    return BucketService()


def _infer_bucket_name(gs_path: str):
    parts = gs_path[5:].split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix


class BucketService:

    async def flatten_bucket(self, gs_path: str):
        """
        This method will flatten all zips in the specified gcp bucket,
        this is: extract them in subfolder to keep them organized and adding them metadata.
        Due to time constraints this is the best solution i have come so far, single threaded,
        could be optimized maybe somehow with multithreading speeding the flatten of zips
        that is a TODO
        """
        bucket_name, prefix = _infer_bucket_name(gs_path)
        bucket = self.__get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=MAX_FILE_PROCESSING)
        for blob in blobs:
            # if not a zip ignore them
            if not blob.name.endswith(".zip"):
                continue
            logger.info(f"Detecting zip: {blob.name}")
            zip_data = blob.download_as_bytes()
            zip_base = PurePosixPath(blob.name).stem  # removes .zip
            base_path = f"{PurePosixPath(blob.name).parent}/{zip_base}"
            with zipfile.ZipFile(io.BytesIO(zip_data)) as archive:

                # Safety checks
                file_list = archive.infolist()
                if len(file_list) > MAX_FILES:
                    logger.warning(f"Skipping {blob.name}: too many files ({len(file_list)} > {MAX_FILES})")
                    continue
                total_uncompressed = sum(f.file_size for f in file_list)
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                    logger.warning(
                        f"Skipping {blob.name}: uncompressed size too big ({total_uncompressed} > {MAX_TOTAL_UNCOMPRESSED})")
                    continue

                for file_info in archive.infolist():
                    if file_info.is_dir():
                        # Ignore subdirs: NOT SUPPORTED
                        logger.warning("Detecting folders in the zip, THIS IS NOT SUPPORTED !! Ignoring...")
                        continue

                    original_filename = PurePosixPath(file_info.filename).name
                    ext = PurePosixPath(original_filename).suffix.lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        logger.warning(f"Unsupported file: {original_filename}, skipping")
                        continue

                    extract_path = f"{base_path}/{original_filename}"

                    with archive.open(file_info) as extracted_file:
                        target_blob = bucket.blob(extract_path)
                        target_blob.upload_from_file(extracted_file)
            logger.info(f"Extracted zip {blob.name}, deleting...")
            blob.delete()

    def __get_bucket(self, bucket_name: str):
        client = storage.Client()
        try:
            bucket = client.get_bucket(bucket_name)
            return bucket
        except NotFound:
            logger.error(f"Bucket {bucket_name} not found aborting...")
            raise RuntimeError(f"Error getting gcp bucket")
        except Forbidden:
            logger.error(f"Permission denied on {bucket_name} check IAM...")
            raise RuntimeError(f"Error getting gcp bucket")
        except Exception as e:
            logger.exception("Unknown error getting bucket")
            raise e

    def list_files(self, gs_path) -> list[Blob]:
        bucket_name, prefix = _infer_bucket_name(gs_path)
        bucket = self.__get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=MAX_FILE_PROCESSING)
        files = []
        for blob in blobs:
            if self.__is_valid_file(blob.name, prefix):
                files.append(blob)
                if len(files) >= MAX_FILE_PROCESSING:
                    break
        return files

    def move_file(self):
        ...

    def __is_valid_file(self, blob_name: str, prefix: str):
        """
        Check if a file in the bucket is valid, this is:
        - Is not a folder
        - is not too nested
        - has the right extension
        """
        # Strip the prefix, e.g. "docs/" from "docs/file1.pdf" => "file1.pdf"
        relative = blob_name[len(prefix):]

        if relative.endswith('/'):
            return False

        depth = relative.count('/')
        if depth > 2:
            return False

        ext = PurePosixPath(blob_name).suffix.lower()
        return ext in ALLOWED_EXTENSIONS

