from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssetState(StrEnum):
    INGESTED = "ingested"
    PROCESSING = "processing"
    READY = "ready"
    DELIVERED = "delivered"


@dataclass
class MediaAsset:
    asset_id: str
    creator_id: str
    source_name: str
    state: AssetState = AssetState.INGESTED
    job_id: str | None = None


class MediaWorkflow:
    def __init__(self) -> None:
        self.assets: dict[str, MediaAsset] = {}

    def ingest(self, asset_id: str, creator_id: str, source_name: str) -> MediaAsset:
        asset = MediaAsset(asset_id, creator_id, source_name)
        self.assets[asset_id] = asset
        return asset

    def start_processing(self, asset_id: str, job_id: str) -> MediaAsset:
        asset = self.assets[asset_id]
        if asset.state != AssetState.INGESTED:
            raise ValueError("only an ingested asset can start processing")
        asset.state = AssetState.PROCESSING
        asset.job_id = job_id
        return asset

    def complete_processing(self, asset_id: str) -> MediaAsset:
        asset = self.assets[asset_id]
        if asset.state != AssetState.PROCESSING:
            raise ValueError("only a processing asset can become ready")
        asset.state = AssetState.READY
        return asset

    def deliver(self, asset_id: str, creator_id: str, otp_verified: bool) -> MediaAsset:
        asset = self.assets[asset_id]
        if not otp_verified or asset.creator_id != creator_id:
            raise PermissionError("verified creator login required")
        if asset.state != AssetState.READY:
            raise ValueError("asset is not ready for delivery")
        asset.state = AssetState.DELIVERED
        return asset
