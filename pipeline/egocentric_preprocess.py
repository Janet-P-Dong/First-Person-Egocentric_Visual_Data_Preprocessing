#!/usr/bin/env python3
"""Local legal-first preprocessing runner for egocentric video.

This starter pipeline intentionally avoids cloud upload and heavy model calls.
It classifies a video into a processing profile using metadata and optional
frame-quality metrics, then generates auditable derived assets with ffmpeg.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


@dataclass
class Governance:
    consent_approved: bool
    audio_approved: bool
    external_processing_approved: bool
    release_approved: bool
    contains_bystanders: bool
    contains_minors: bool
    contains_health_context: bool
    biometric_or_emotion_inference: bool
    jurisdiction: str
    capture_context: str

    @property
    def sensitive_flags(self) -> list[str]:
        flags: list[str] = []
        if self.contains_bystanders:
            flags.append("bystanders")
        if self.contains_minors:
            flags.append("minors")
        if self.contains_health_context:
            flags.append("health_context")
        if self.biometric_or_emotion_inference:
            flags.append("biometric_or_emotion_inference")
        if not self.audio_approved:
            flags.append("audio_not_approved")
        if not self.external_processing_approved:
            flags.append("external_processing_not_approved")
        if not self.release_approved:
            flags.append("release_not_approved")
        return flags


@dataclass
class VideoMetrics:
    blur_laplacian_mean: float | None
    brightness_mean: float | None
    motion_mean_absdiff: float | None
    sampled_frames: int
    metrics_available: bool
    metrics_note: str


@dataclass
class ProcessingPlan:
    video_type: str
    profile: str
    required_processing: list[str]
    prohibited_or_deferred_processing: list[str]
    reasons: list[str]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required binary not found on PATH: {name}")


def ffprobe_metadata(video_path: Path) -> dict[str, Any]:
    require_binary("ffprobe")
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )
    return json.loads(result.stdout)


def parse_fraction(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            denominator_float = float(denominator)
            if denominator_float == 0:
                return None
            return float(numerator) / denominator_float
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def summarize_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    streams = raw.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    duration = raw.get("format", {}).get("duration") or video_stream.get("duration")
    fps = parse_fraction(video_stream.get("avg_frame_rate")) or parse_fraction(video_stream.get("r_frame_rate"))
    width = video_stream.get("width")
    height = video_stream.get("height")
    return {
        "duration_seconds": float(duration) if duration is not None else None,
        "fps": fps,
        "width": int(width) if width is not None else None,
        "height": int(height) if height is not None else None,
        "video_codec": video_stream.get("codec_name"),
        "audio_present": bool(audio_streams),
        "audio_codecs": sorted({s.get("codec_name") for s in audio_streams if s.get("codec_name")}),
        "format_name": raw.get("format", {}).get("format_name"),
        "bit_rate": raw.get("format", {}).get("bit_rate"),
        "stream_count": len(streams),
    }


def compute_frame_metrics(video_path: Path, sample_frames: int) -> VideoMetrics:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency path
        return VideoMetrics(None, None, None, 0, False, f"OpenCV metrics unavailable: {exc}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return VideoMetrics(None, None, None, 0, False, "OpenCV could not open video")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames <= 0:
        cap.release()
        return VideoMetrics(None, None, None, 0, False, "OpenCV could not determine frame count")

    indices = sorted({int(i) for i in np.linspace(0, max(total_frames - 1, 0), sample_frames)})
    blur_values: list[float] = []
    brightness_values: list[float] = []
    motion_values: list[float] = []
    previous_gray = None

    for index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_values.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        brightness_values.append(float(gray.mean()))
        if previous_gray is not None:
            resized = cv2.resize(gray, (previous_gray.shape[1], previous_gray.shape[0]))
            motion_values.append(float(np.mean(cv2.absdiff(resized, previous_gray))))
        previous_gray = gray

    cap.release()
    if not blur_values:
        return VideoMetrics(None, None, None, 0, False, "No readable sampled frames")

    return VideoMetrics(
        blur_laplacian_mean=sum(blur_values) / len(blur_values),
        brightness_mean=sum(brightness_values) / len(brightness_values),
        motion_mean_absdiff=(sum(motion_values) / len(motion_values)) if motion_values else None,
        sampled_frames=len(blur_values),
        metrics_available=True,
        metrics_note="Computed with OpenCV sampled frames",
    )


def infer_video_type(
    video_path: Path,
    metadata: dict[str, Any],
    metrics: VideoMetrics,
    governance: Governance,
) -> ProcessingPlan:
    duration = metadata.get("duration_seconds") or 0
    fps = metadata.get("fps") or 0
    height = metadata.get("height") or 0
    filename = video_path.name.lower()
    reasons: list[str] = []
    required: list[str] = [
        "metadata_validation",
        "checksum",
        "privacy_prescan",
        "session_manifest",
    ]
    deferred: list[str] = []

    sensitive = governance.sensitive_flags
    if sensitive:
        reasons.append(f"sensitive_governance_flags={','.join(sensitive)}")
        required.extend(["restricted_access", "manual_privacy_review"])

    if not governance.consent_approved:
        return ProcessingPlan(
            video_type="blocked_unapproved_capture",
            profile="governance_blocked",
            required_processing=["legal_review", "consent_resolution"],
            prohibited_or_deferred_processing=["derived_media_generation", "model_inference", "cloud_upload", "dataset_release"],
            reasons=["consent_approved=false"],
        )

    if duration >= 600:
        video_type = "long_untrimmed_egocentric"
        required.extend(["scene_change_keyframes", "fixed_window_clips", "temporal_segmentation"])
        reasons.append("duration>=600s")
    elif duration <= 30:
        video_type = "short_clip"
        required.extend(["dense_keyframes", "clip_level_classification"])
        reasons.append("duration<=30s")
    else:
        video_type = "medium_session"
        required.extend(["regular_keyframes", "fixed_window_clips"])
        reasons.append("30s<duration<600s")

    if metrics.metrics_available and metrics.motion_mean_absdiff is not None:
        if metrics.motion_mean_absdiff >= 35:
            video_type = "high_motion_first_person"
            required.extend(["motion_aware_sampling", "stabilization_quality_flag"])
            reasons.append("high sampled frame difference")
        elif metrics.motion_mean_absdiff <= 8 and duration > 60:
            required.append("low_motion_duplicate_filter")
            reasons.append("low sampled frame difference")

    if metrics.metrics_available and metrics.blur_laplacian_mean is not None and metrics.blur_laplacian_mean < 60:
        required.append("blur_quality_flag")
        reasons.append("low laplacian blur score")

    if height and height < 720:
        required.append("low_resolution_quality_flag")
        reasons.append("height<720")

    if fps and fps < 20:
        required.append("low_fps_quality_flag")
        reasons.append("fps<20")

    privacy_hints = ["clinic", "hospital", "school", "child", "kid", "therapy", "home", "patient"]
    if any(hint in filename for hint in privacy_hints):
        required.append("filename_sensitive_context_review")
        reasons.append("filename suggests sensitive context")

    if metadata.get("audio_present") and not governance.audio_approved:
        required.append("strip_audio_from_derivatives")
        deferred.append("audio_transcription")
        reasons.append("audio present but not approved")

    if not governance.external_processing_approved:
        deferred.extend(["external_vlm_api", "third_party_cloud_inference"])
        reasons.append("external processing not approved")

    if not governance.release_approved:
        deferred.append("public_dataset_release")
        reasons.append("release not approved")

    if governance.contains_minors or governance.contains_health_context or governance.biometric_or_emotion_inference:
        profile = "restricted_sensitive_research"
    elif video_type == "long_untrimmed_egocentric":
        profile = "long_form_segmentation"
    elif video_type == "high_motion_first_person":
        profile = "high_motion_quality_control"
    else:
        profile = "standard_local_preprocessing"

    return ProcessingPlan(
        video_type=video_type,
        profile=profile,
        required_processing=sorted(set(required)),
        prohibited_or_deferred_processing=sorted(set(deferred)),
        reasons=reasons,
    )


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transcode_analysis_video(
    video_path: Path,
    output_path: Path,
    keep_audio: bool,
    max_height: int,
) -> None:
    require_binary("ffmpeg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=-2:min({max_height}\\,ih)"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
    ]
    if keep_audio:
        command.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        command.append("-an")
    command.append(str(output_path))
    run_command(command)


def extract_keyframes(video_path: Path, output_dir: Path, interval_seconds: int, max_height: int) -> list[str]:
    require_binary("ffmpeg")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "keyframe_%05d.jpg"
    vf = f"fps=1/{interval_seconds},scale=-2:min({max_height}\\,ih)"
    run_command(["ffmpeg", "-y", "-i", str(video_path), "-vf", vf, "-q:v", "3", str(pattern)])
    return sorted(p.name for p in output_dir.glob("keyframe_*.jpg"))


def extract_fixed_window_clips(
    video_path: Path,
    output_dir: Path,
    duration_seconds: float,
    clip_seconds: int,
    keep_audio: bool,
) -> list[dict[str, Any]]:
    require_binary("ffmpeg")
    output_dir.mkdir(parents=True, exist_ok=True)
    if duration_seconds <= 0:
        return []

    clip_count = max(1, math.ceil(duration_seconds / clip_seconds))
    clips: list[dict[str, Any]] = []
    for idx in range(clip_count):
        start = idx * clip_seconds
        length = min(clip_seconds, max(duration_seconds - start, 0))
        if length <= 0:
            continue
        output_path = output_dir / f"clip_{idx:05d}_{int(start):06d}s.mp4"
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{length:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
        ]
        if keep_audio:
            command.extend(["-c:a", "aac", "-b:a", "96k"])
        else:
            command.append("-an")
        command.append(str(output_path))
        run_command(command)
        clips.append({"clip_path": output_path.name, "start_seconds": start, "end_seconds": start + length})
    return clips


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legal-first local preprocessing for egocentric video.")
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output dataset/session directory")
    parser.add_argument("--session-id", default=None, help="Stable session ID; defaults to video stem")
    parser.add_argument("--jurisdiction", default="unspecified", help="Legal jurisdiction for the capture")
    parser.add_argument("--capture-context", default="unspecified", help="Capture context, e.g. lab/home/school/clinic")
    parser.add_argument("--consent-approved", action="store_true", help="Required to generate derived media")
    parser.add_argument("--audio-approved", action="store_true", help="Allow audio in derived outputs")
    parser.add_argument("--external-processing-approved", action="store_true", help="Allow external/cloud model inference")
    parser.add_argument("--release-approved", action="store_true", help="Allow public/release-ready output status")
    parser.add_argument("--contains-bystanders", action="store_true")
    parser.add_argument("--contains-minors", action="store_true")
    parser.add_argument("--contains-health-context", action="store_true")
    parser.add_argument("--biometric-or-emotion-inference", action="store_true")
    parser.add_argument("--sample-frames", type=int, default=24)
    parser.add_argument("--keyframe-interval", type=int, default=5)
    parser.add_argument("--clip-seconds", type=int, default=10)
    parser.add_argument("--max-height", type=int, default=720)
    parser.add_argument("--dry-run", action="store_true", help="Write manifests and plan only; no media derivatives")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    video_path = args.video.expanduser().resolve()
    if not video_path.exists():
        print(f"Input video does not exist: {video_path}", file=sys.stderr)
        return 1
    if video_path.suffix.lower() not in VIDEO_SUFFIXES:
        print(f"Warning: uncommon video suffix {video_path.suffix}", file=sys.stderr)

    session_id = args.session_id or video_path.stem
    session_dir = args.output_dir.expanduser().resolve() / session_id
    metadata_dir = session_dir / "metadata"
    derivatives_dir = session_dir / "derivatives"

    governance = Governance(
        consent_approved=args.consent_approved,
        audio_approved=args.audio_approved,
        external_processing_approved=args.external_processing_approved,
        release_approved=args.release_approved,
        contains_bystanders=args.contains_bystanders,
        contains_minors=args.contains_minors,
        contains_health_context=args.contains_health_context,
        biometric_or_emotion_inference=args.biometric_or_emotion_inference,
        jurisdiction=args.jurisdiction,
        capture_context=args.capture_context,
    )

    raw_metadata = ffprobe_metadata(video_path)
    metadata = summarize_metadata(raw_metadata)
    metrics = compute_frame_metrics(video_path, args.sample_frames)
    plan = infer_video_type(video_path, metadata, metrics, governance)

    run_manifest: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "input_video": str(video_path),
        "input_video_sha256": sha256_file(video_path),
        "output_dir": str(session_dir),
        "governance": asdict(governance),
        "metadata": metadata,
        "frame_metrics": asdict(metrics),
        "processing_plan": asdict(plan),
        "dry_run": args.dry_run,
    }

    write_json(metadata_dir / "ffprobe_raw.json", raw_metadata)
    write_json(metadata_dir / "session_manifest.json", run_manifest)
    write_json(metadata_dir / "governance.json", asdict(governance))
    write_json(metadata_dir / "processing_plan.json", asdict(plan))

    if plan.profile == "governance_blocked":
        print(json.dumps({"status": "blocked_by_governance", "manifest": str(metadata_dir / "session_manifest.json")}, indent=2))
        return 2

    if args.dry_run:
        print(json.dumps({"status": "dry_run_complete", "manifest": str(metadata_dir / "session_manifest.json")}, indent=2))
        return 0

    keep_audio = bool(governance.audio_approved and metadata.get("audio_present"))
    analysis_video = derivatives_dir / "analysis_video.mp4"
    transcode_analysis_video(video_path, analysis_video, keep_audio=keep_audio, max_height=args.max_height)
    keyframes = extract_keyframes(
        video_path,
        derivatives_dir / "keyframes",
        interval_seconds=max(args.keyframe_interval, 1),
        max_height=args.max_height,
    )
    clips = extract_fixed_window_clips(
        video_path,
        derivatives_dir / "clips",
        duration_seconds=float(metadata.get("duration_seconds") or 0),
        clip_seconds=max(args.clip_seconds, 1),
        keep_audio=keep_audio,
    )

    outputs = {
        "analysis_video": str(analysis_video.relative_to(session_dir)),
        "keyframes": keyframes,
        "clips": clips,
        "audio_in_derivatives": keep_audio,
    }
    run_manifest["outputs"] = outputs
    write_json(metadata_dir / "session_manifest.json", run_manifest)
    write_json(metadata_dir / "outputs_manifest.json", outputs)

    print(json.dumps({"status": "complete", "manifest": str(metadata_dir / "session_manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
