"""
app/utils/exceptions.py

Centralized translation of exceptions raised by the ML pipeline into
HTTP responses.

The pipeline (``build_prediction_features.py``, ``predict_player_performance.py``,
``series_simulator.py``) already raises specific, well-documented
exception types for specific failure modes -- this module's only job is
to map those to sensible HTTP status codes, in exactly one place, so
individual routers never need their own try/except blocks around calls
into the pipeline.

Mapping used:
    ValueError       -> 422 Unprocessable Entity
        Covers invalid PredictionRequest/SeriesFixture input (bad team,
        bad opponent, out-of-range innings_number/batting_position,
        unparsable match_date) and an unrecognised player when
        allow_debut/allow_debutants is False. Also covers an upstream
        feature-column-count mismatch raised by
        ``build_prediction_features._select_prediction_feature_vector``;
        that particular case is a pipeline drift issue rather than a
        client input problem, but the pipeline raises it as a plain
        ValueError with no distinct type to key off, so it is mapped
        here alongside genuine input errors. See that function's own
        docstring if this ever needs finer-grained handling.
    FileNotFoundError -> 503 Service Unavailable
        Raised when the saved preprocessor/model artifacts are missing.
        Treated as a deployment/infrastructure issue, not a client error.
    RuntimeError      -> 500 Internal Server Error
        Raised on internal pipeline integrity failures (e.g. a
        synthetic Match_ID collision) that indicate a bug rather than
        anything the caller did wrong.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
 
    log.warning(f"Validation error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def _file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
   
    log.error(f"Model artifacts unavailable on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Model artifacts are unavailable. " + str(exc)},
    )


async def _runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
   
    log.exception(f"Internal pipeline error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred while processing this request."},
    )


def register_exception_handlers(app: FastAPI) -> None:
 
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(FileNotFoundError, _file_not_found_handler)
    app.add_exception_handler(RuntimeError, _runtime_error_handler)