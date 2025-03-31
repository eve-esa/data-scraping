import json
import re
import pdfplumber
import fitz
import io
from dotenv import load_dotenv

from model.sql_models import UploadedResource, UploadedResourceMetadata
from repository.uploaded_resource_metadata_repository import UploadedResourceMetadataRepository
from repository.uploaded_resource_repository import UploadedResourceRepository
from service.storage import S3Storage


load_dotenv()
client_storage = S3Storage()


def match(first_page_text: str) -> bool:
    cc_by_text_match = re.search(r'CC[-\s]?BY', first_page_text, re.IGNORECASE)

    cc_variants = [
        "Creative Commons",
        "CC-BY",
        # "Attribution",
        # "CC Attribution",
        "Creative Commons Attribution"
    ]

    text_match = any(
        variant.lower() in first_page_text.lower()
        for variant in cc_variants
    )

    return bool(cc_by_text_match or text_match)


def with_pdf_plumber(pdf_key: str) -> bool:
    try:
        pdf_byte_content = client_storage.get(pdf_key)

        with pdfplumber.open(io.BytesIO(pdf_byte_content)) as pdf:
            first_page_text = pdf.pages[0].extract_text()

        if not first_page_text:
            print("License CC-BY not found in the first page")
            return False

        return match(first_page_text)
    except Exception as e:
        print(f"Error during the elaboration of the PDF: {e}")
        return False


def with_pymupdf(pdf_key: str) -> bool:
    pdf_document = None
    result = False

    try:
        pdf_byte_content = client_storage.get(pdf_key)

        pdf_document = fitz.open(stream=pdf_byte_content, filetype="pdf")
        first_page_text = pdf_document[0].get_text()

        return match(first_page_text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during the elaboration of the PDF: {e}")
    finally:
        if pdf_document is not None:
            pdf_document.close()

        return result


def process_uploaded_resource(uploaded_resource: UploadedResource) -> UploadedResourceMetadata | None:
    """
    Process the uploaded resource to check if it has a CC-BY license.
    """
    if not uploaded_resource.success or not uploaded_resource.bucket_key:
        return None

    pdf_key = uploaded_resource.bucket_key

    # Check if the PDF has a CC-BY license using pdfplumber
    cc_by_license = with_pdf_plumber(pdf_key)

    # If pdfplumber fails, try with pymupdf
    if not cc_by_license:
        cc_by_license = with_pymupdf(pdf_key)

    # Save the metadata to the database
    metadata = UploadedResourceMetadata(
        uploaded_resource=uploaded_resource,
        metadata=json.dumps({"cc-by-license": cc_by_license}),
    )

    repository = UploadedResourceMetadataRepository()
    metadata_id = repository.upsert(metadata, {"uploaded_resource_id": uploaded_resource.id})

    metadata.id = metadata_id

    return metadata


res = {
    "cc-by": 0,
    "no-cc-by": 0,
}
resources = UploadedResourceRepository().get_by(conditions={"scraper": "AMSScraper"})
for resource in resources:
    metadata_ = process_uploaded_resource(resource)

    if metadata_ is None:
        continue

    if metadata_.metadata_json["cc-by-license"]:
        res["cc-by"] += 1
    else:
        res["no-cc-by"] += 1

print(f"CC-BY: {res['cc-by']}, NO CC-BY: {res['no-cc-by']}")
