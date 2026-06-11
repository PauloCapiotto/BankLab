from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import APIError
from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router

app = FastAPI(title="BankLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {"field": ".".join(str(part) for part in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Dados inválidos. Verifique os campos e tente novamente.",
            "details": {"errors": errors},
        },
    )


app.include_router(auth_router)
app.include_router(accounts_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
