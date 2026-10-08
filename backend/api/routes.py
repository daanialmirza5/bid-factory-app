from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
import io

from backend.models.entities import Bid, Requirement, Review
from backend.schemas.requests import ReviewRequest
from backend.schemas.responses import AnalysisResponse, GenerateResponse, UploadResponse
from backend.schemas.response_generation import ProposedBidResponse, ProposedResponseRequest
from backend.schemas.review import ReviewCollectionResponse, ReviewCommentRequest, ReviewItem, ReviewStatus, ReviewStatusResponse
from backend.schemas.orchestration import BidAnalysisResult
from backend.services.repository import repository
from backend.services.rocketride_service import rocketride_service
from backend.utils.config import get_settings
from backend.utils.uploads import read_and_validate_upload
from backend.services.response_generation import response_generation_service
from backend.services.review import ReviewService
from backend.services.orchestration import bid_analysis_orchestrator
from backend.services.export_service import export_service


router = APIRouter()
review_service = ReviewService(repository)


@router.post(
    "/bids/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["bids"],
)
async def upload_bid(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> UploadResponse:
    contents, file_type = await read_and_validate_upload(file, get_settings().max_upload_size_bytes)
    bid = repository.create_bid(
        filename=file.filename or "uploaded-rfp",
        title=title or file.filename or "Untitled bid",
        content_type=file.content_type,
        file_type=file_type,
        file_size=len(contents),
        document=contents,
    )
    
    # Safely inject into Neo4j graph without blocking
    try:
        from backend.services.graph_service import graph_rag
        if graph_rag.driver:
            with graph_rag.driver.session() as session:
                session.run(
                    "CREATE (r:RFP {id: $id, title: $title, uploaded_at: timestamp()}) "
                    "WITH r MATCH (m:Policy) MERGE (r)-[:EVALUATING]->(m)",
                    id=str(bid.bid_id), title=bid.rfp.title
                )
    except Exception as e:
        print(f"Graph Neo4j bypass on upload: {e}")
    return UploadResponse(
        bid_id=bid.bid_id,
        filename=bid.rfp.filename,
        file_type=bid.rfp.file_type,
        upload_timestamp=bid.rfp.uploaded_at,
        processing_status=bid.processing_status.value,
        bid=bid,
    )


@router.post(
    "/bids/{bid_id}/analyze",
    response_model=BidAnalysisResult,
    responses={503: {"model": BidAnalysisResult, "description": "AI processing failed; see errors."}},
    tags=["bids"],
)
async def analyze_bid(bid_id: UUID) -> BidAnalysisResult | JSONResponse:
    bid = repository.get_bid(bid_id)
    result = await bid_analysis_orchestrator.analyze(bid, repository.get_document(bid_id))
    if result.processing_status == "failed":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result.model_dump(mode="json"))

    # Save the analyzed requirements into the database so the UI can fetch them
    from backend.models.entities import Requirement
    for i, ext_req in enumerate(result.requirements):
        req = Requirement(
            id=ext_req.requirement_id,
            requirement_id=ext_req.requirement_id,
            bid_id=bid_id,
            reference=f"REQ-{i+1}",
            text=ext_req.requirement_text,
            requirement_text=ext_req.requirement_text,
            category=ext_req.category,
            priority=ext_req.priority,
            deadline=ext_req.deadline,
            compliance_type=ext_req.compliance_type,
            source_section=ext_req.source_section,
            source_page=ext_req.source_page
        )
        repository._requirements[req.id] = req
        
    return result


@router.get("/bids/{bid_id}", response_model=Bid, tags=["bids"])
def get_bid(bid_id: UUID) -> Bid:
    return repository.get_bid(bid_id)


@router.get("/bids", response_model=list[Bid], tags=["bids"])
def get_all_bids() -> list[Bid]:
    return list(repository._bids.values())


@router.get(
    "/bids/{bid_id}/requirements",
    response_model=list[Requirement],
    tags=["requirements"],
)
def get_requirements(bid_id: UUID) -> list[Requirement]:
    repository.get_bid(bid_id)
    return repository.get_requirements(bid_id)


@router.post(
    "/requirements/{requirement_id}/review",
    response_model=Review,
    status_code=status.HTTP_201_CREATED,
    tags=["reviews"],
)
def review_requirement(requirement_id: UUID, request: ReviewRequest) -> Review:
    return repository.add_review(requirement_id, request)


@router.post(
    "/bids/{bid_id}/generate",
    response_model=GenerateResponse,
    tags=["bids"],
)
async def generate_bid(bid_id: UUID) -> GenerateResponse:
    bid = repository.get_bid(bid_id)
    result = await rocketride_service.generate(bid, repository.get_document(bid_id))
    return GenerateResponse(bid_id=bid.id, **result)


@router.post(
    "/bids/{bid_id}/responses",
    response_model=ProposedBidResponse,
    tags=["responses"],
)
def generate_proposed_responses(bid_id: UUID, request: ProposedResponseRequest) -> ProposedBidResponse:
    repository.get_bid(bid_id)
    response = response_generation_service.generate(request.requirements, request.compliance_results)
    review_ids = [
        str(review_service.create_pending(
            bid_id=bid_id,
            requirement_id=generated.requirement_id,
            proposed_response=generated.proposed_response,
            compliance_status=generated.compliance_status,
            confidence=generated.confidence,
            supporting_evidence=generated.supporting_evidence,
        ).review_id)
        for generated in response.responses
    ]
    response.review_ids = review_ids
    return response


@router.get("/bids/{bid_id}/export/docx", tags=["bids"])
def export_bid_docx(bid_id: UUID) -> StreamingResponse:
    content = export_service.generate_docx(bid_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_compiled.docx"}
    )

@router.get("/bids/{bid_id}/export/csv", tags=["bids"])
def export_bid_csv(bid_id: UUID) -> StreamingResponse:
    content = export_service.generate_csv(bid_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=compliance_matrix_{bid_id}.csv"}
    )

from fastapi.responses import FileResponse
import os

@router.get("/download/demo-docx")
def download_demo_docx():
    path = os.path.join(os.getcwd(), "demo_assets", "Golden_Demo_RFP.docx")
    return FileResponse(path, filename="Golden_Demo_RFP.docx")

@router.get("/download/demo-image")
def download_demo_image():
    path = os.path.join(os.getcwd(), "demo_assets", "Scanned_RFP_Table.png")
    return FileResponse(path, filename="Scanned_RFP_Table.png")


@router.get("/bids/{bid_id}/reviews", response_model=ReviewCollectionResponse, tags=["reviews"])
def list_review_items(bid_id: UUID) -> ReviewCollectionResponse:
    repository.get_bid(bid_id)
    return ReviewCollectionResponse(bid_id=bid_id, items=review_service.list_for_bid(bid_id))


@router.get("/reviews/{review_id}", response_model=ReviewItem, tags=["reviews"])
def get_review_item(review_id: UUID) -> ReviewItem:
    return review_service.get_item(review_id)


@router.get("/reviews", response_model=ReviewCollectionResponse, tags=["reviews"])
def get_all_reviews() -> ReviewCollectionResponse:
    items = list(repository._review_items.values())
    return ReviewCollectionResponse(
        items=items,
        total_pending=sum(1 for r in items if r.review_status == "PENDING"),
        total_approved=sum(1 for r in items if r.review_status == "APPROVED"),
        total_rejected=sum(1 for r in items if r.review_status == "REJECTED"),
        total_needs_revision=sum(1 for r in items if r.review_status == "NEEDS_REVISION"),
    )


@router.post("/reviews/{review_id}/approve", response_model=ReviewItem, tags=["reviews"])
def approve_review(review_id: UUID, request: ReviewCommentRequest | None = None) -> ReviewItem:
    return review_service.transition(review_id, ReviewStatus.approved, request.reviewer_comment if request else None, request.reviewer if request else None)


@router.post("/reviews/{review_id}/reject", response_model=ReviewItem, tags=["reviews"])
def reject_review(review_id: UUID, request: ReviewCommentRequest) -> ReviewItem:
    return review_service.transition(review_id, ReviewStatus.rejected, request.reviewer_comment, request.reviewer)


@router.post("/reviews/{review_id}/needs-revision", response_model=ReviewItem, tags=["reviews"])
def request_revision(review_id: UUID, request: ReviewCommentRequest) -> ReviewItem:
    return review_service.transition(review_id, ReviewStatus.needs_revision, request.reviewer_comment, request.reviewer)


@router.patch("/reviews/{review_id}/comment", response_model=ReviewItem, tags=["reviews"])
def update_review_comment(review_id: UUID, request: ReviewCommentRequest) -> ReviewItem:
    return review_service.update_comment(review_id, request)


@router.get("/bids/{bid_id}/review-status", response_model=ReviewStatusResponse, tags=["reviews"])
def get_review_status(bid_id: UUID) -> ReviewStatusResponse:
    repository.get_bid(bid_id)
    return review_service.get_status(bid_id)