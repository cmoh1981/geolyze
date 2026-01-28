from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Any


class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class AnalyzeRequest(BaseModel):
    geo_id: str = Field(..., pattern=r"^GSE\d+$", description="GEO Series accession ID")


class AnalyzeResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    geo_id: str
    status: JobStatus
    progress: int = Field(..., ge=0, le=100)
    message: str
    created_at: str
    completed_at: Optional[str] = None


class JobResultsResponse(BaseModel):
    job_id: str
    geo_id: str
    metadata: dict
    data_type: str  # "single_cell" or "bulk"
    plots: dict[str, Any]  # plot_name -> Plotly JSON dict
    summary: dict  # n_genes, n_samples, n_clusters, etc.
    de_results: Optional[list[dict]] = None  # top DE genes
