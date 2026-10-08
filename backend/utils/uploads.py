from pathlib import Path

from fastapi import HTTPException, UploadFile, status


ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}


def validate_upload_metadata(filename: str | None, content_type: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A filename is required.")

    extension = Path(filename).suffix.lower()
    allowed_mime_types = ALLOWED_FILE_TYPES.get(extension)
    if allowed_mime_types is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Only PDF and DOCX files are accepted.",
        )
    if content_type and content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid content type for {extension} upload.",
        )
    return extension.removeprefix(".")


async def read_and_validate_upload(file: UploadFile, max_size: int) -> tuple[bytes, str]:
    file_type = validate_upload_metadata(file.filename, file.content_type)
    contents = await file.read(max_size + 1)
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum allowed size is {max_size} bytes.",
        )

    if file_type == "pdf" and not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The upload is not a valid PDF file.")
    if file_type == "docx" and not contents.startswith(b"PK"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The upload is not a valid DOCX file.")
    if file_type in ["png", "jpg", "jpeg"]:
        pass # allow image headers
    return contents, file_type