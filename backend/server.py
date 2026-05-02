import tempfile  # to create a file on disk for semgrep_scan
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    ModelSettings,
    Runner,
    trace,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)

from context import SECURITY_RESEARCHER_INSTRUCTIONS, get_analysis_prompt, enhance_summary
from mcp_servers import create_semgrep_server

load_dotenv(override=True)

_OPENROUTER_DEFAULT_BASE = "https://openrouter.ai/api/v1"
# OpenRouter model ids use a provider prefix, e.g. openai/gpt-4.1-mini
_OPENROUTER_DEFAULT_MODEL = "openai/gpt-4.1-mini"
_OPENAI_DEFAULT_MODEL = "gpt-4.1-mini"
# OpenRouter rejects huge max_tokens vs credits; cap completions when using OpenRouter.
_OPENROUTER_DEFAULT_MAX_TOKENS = 4096


def _parse_positive_int(env_name: str) -> int | None:
    raw = (os.getenv(env_name) or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def get_model_settings() -> ModelSettings:
    """Cap completion tokens for OpenRouter credits; optional overrides via env."""
    llm_cap = _parse_positive_int("LLM_MAX_TOKENS")
    if llm_cap is not None:
        return ModelSettings(max_tokens=llm_cap)

    if (os.getenv("OPENROUTER_API_KEY") or "").strip():
        or_cap = _parse_positive_int("OPENROUTER_MAX_TOKENS")
        return ModelSettings(
            max_tokens=or_cap if or_cap is not None else _OPENROUTER_DEFAULT_MAX_TOKENS
        )

    return ModelSettings()


def configure_llm() -> None:
    """If OPENROUTER_API_KEY is set, route LLM calls through OpenRouter (OpenAI-compatible API)."""
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        return

    base_url = (os.getenv("OPENROUTER_BASE_URL") or _OPENROUTER_DEFAULT_BASE).rstrip("/")
    client = AsyncOpenAI(base_url=base_url, api_key=key)
    set_default_openai_client(client, use_for_tracing=False)
    # OpenRouter exposes chat completions; the Agents SDK defaults to the Responses API on OpenAI.
    set_default_openai_api("chat_completions")
    # Avoid sending traces to api.openai.com without an OpenAI key.
    set_tracing_disabled(True)


configure_llm()


def get_llm_model() -> str:
    """Prefer LLM_MODEL, then OPENROUTER_MODEL, then provider-appropriate defaults."""
    if os.getenv("LLM_MODEL"):
        return os.getenv("LLM_MODEL", _OPENAI_DEFAULT_MODEL)
    if os.getenv("OPENROUTER_MODEL"):
        return os.getenv("OPENROUTER_MODEL", _OPENROUTER_DEFAULT_MODEL)
    if (os.getenv("OPENROUTER_API_KEY") or "").strip():
        return _OPENROUTER_DEFAULT_MODEL
    return _OPENAI_DEFAULT_MODEL

app = FastAPI(title="Cybersecurity Analyzer API")

# Configure CORS for development and production
cors_origins = [
    "http://localhost:3000",  # Local development
    "http://frontend:3000",  # Docker development
]

# In production, allow same-origin requests (static files served from same domain)
if os.getenv("ENVIRONMENT") == "production":
    cors_origins.append(
        "*"
    )  # Allow all origins in production since we serve frontend from same domain

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    code: str


class SecurityIssue(BaseModel):
    title: str = Field(description="Brief title of the security vulnerability")
    description: str = Field(
        description="Detailed description of the security issue and its potential impact"
    )
    code: str = Field(
        description="The specific vulnerable code snippet that demonstrates the issue"
    )
    fix: str = Field(description="Recommended code fix or mitigation strategy")
    cvss_score: float = Field(description="CVSS score from 0.0 to 10.0 representing severity")
    severity: str = Field(description="Severity level: critical, high, medium, or low")


class SecurityReport(BaseModel):
    summary: str = Field(description="Executive summary of the security analysis")
    issues: List[SecurityIssue] = Field(description="List of identified security vulnerabilities")


def validate_request(request: AnalyzeRequest) -> None:
    """Validate the analysis request."""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided for analysis")


def check_api_keys() -> None:
    """Verify an LLM API key is configured (OpenAI and/or OpenRouter)."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_openrouter = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())
    if not has_openai and not has_openrouter:
        raise HTTPException(
            status_code=500,
            detail="Configure OPENAI_API_KEY or OPENROUTER_API_KEY in your environment",
        )


def create_security_agent(semgrep_server) -> Agent:
    """Create and configure the security analysis agent."""
    return Agent(
        name="Security Researcher",
        instructions=SECURITY_RESEARCHER_INSTRUCTIONS,
        model=get_llm_model(),
        model_settings=get_model_settings(),
        mcp_servers=[semgrep_server],
        output_type=SecurityReport,
    )


async def run_security_analysis(code: str) -> SecurityReport:
    """Execute the security analysis workflow."""
    with trace("Security Researcher"):
        async with create_semgrep_server() as semgrep:
            agent = create_security_agent(semgrep)
            try:
                with tempfile.NamedTemporaryFile(  # Creates a temporary file locally with teh code
                    mode="w", suffix=".py", delete=False
                ) as temp:
                    temp.write(code)
                    temp_path = temp.name
                try:
                    result = await Runner.run(
                        agent, input=get_analysis_prompt(code, temp_path)
                    )  # Sends code and path to the file
                    # Changed the following two lines to sort by CVSS in descending order
                    sorted_report = result.final_output_as(SecurityReport)
                    sorted_report.issues.sort(key=lambda issue: issue.cvss_score, reverse=True)

                    return sorted_report
                finally:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=}")
                raise


def format_analysis_response(code: str, report: SecurityReport) -> SecurityReport:
    """Format the final analysis response."""
    enhanced_summary = enhance_summary(len(code), report.summary)
    return SecurityReport(summary=enhanced_summary, issues=report.issues)


@app.post("/api/analyze", response_model=SecurityReport)
async def analyze_code(request: AnalyzeRequest) -> SecurityReport:
    """
    Analyze Python code for security vulnerabilities using OpenAI Agents and Semgrep.

    This endpoint combines static analysis via Semgrep with AI-powered security analysis
    to provide comprehensive vulnerability detection and remediation guidance.
    """
    validate_request(request)
    check_api_keys()

    try:
        report = await run_security_analysis(request.code)
        return format_analysis_response(request.code, report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"message": "Cybersecurity Analyzer API"}


# Mount static files for frontend
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
