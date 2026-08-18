from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_sms import InfraiError, InfraiSmsClient
from .login_service import LoginService
from .media_workflow import MediaWorkflow

app = FastAPI(title="Creator media login")
workflow = MediaWorkflow()


class CodeRequest(BaseModel):
    phone: Annotated[str, Field(min_length=8, max_length=20)]
    request_id: Annotated[str, Field(min_length=8, max_length=100)]


class CodeVerification(CodeRequest):
    code: Annotated[str, Field(min_length=4, max_length=10)]


class AssetIngest(BaseModel):
    asset_id: str
    creator_id: str
    source_name: str


class ProcessingJob(BaseModel):
    job_id: str


class DeliveryRequest(BaseModel):
    creator_id: str
    otp_verified: bool


def login_service() -> LoginService:
    return LoginService(InfraiSmsClient())


def rejection(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code})


@app.post("/login/code", status_code=202)
def request_code(body: CodeRequest, service: LoginService = Depends(login_service)) -> dict[str, str]:
    try:
        service.request_code(body.phone, body.request_id)
    except InfraiError as error:
        raise rejection(error) from error
    return {"status": "code_sent"}


@app.post("/login/verify")
def verify_code(body: CodeVerification, service: LoginService = Depends(login_service)) -> dict[str, bool]:
    try:
        verified = service.verify_code(body.phone, body.code, body.request_id)
    except InfraiError as error:
        raise rejection(error) from error
    return {"verified": verified}


@app.post("/assets", status_code=201)
def ingest_asset(body: AssetIngest) -> dict[str, str]:
    asset = workflow.ingest(body.asset_id, body.creator_id, body.source_name)
    return {"asset_id": asset.asset_id, "state": asset.state}


@app.post("/assets/{asset_id}/jobs")
def start_job(asset_id: str, body: ProcessingJob) -> dict[str, str]:
    asset = workflow.start_processing(asset_id, body.job_id)
    return {"asset_id": asset.asset_id, "state": asset.state, "job_id": body.job_id}


@app.post("/assets/{asset_id}/jobs/complete")
def complete_job(asset_id: str) -> dict[str, str]:
    asset = workflow.complete_processing(asset_id)
    return {"asset_id": asset.asset_id, "state": asset.state}


@app.post("/assets/{asset_id}/delivery")
def deliver_asset(asset_id: str, body: DeliveryRequest) -> dict[str, str]:
    try:
        asset = workflow.deliver(asset_id, body.creator_id, body.otp_verified)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"asset_id": asset.asset_id, "state": asset.state}
