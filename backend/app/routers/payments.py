"""
Rutas del cliente para pagos SINPE Móvil: consultar planes, datos de la cuenta
SINPE y subir el comprobante de transferencia.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser, get_current_user
from app.services import sinpe_service, storage_service
from app.schemas.payment import SinpePaymentCreateResponse, PlanInfo, SinpePaymentHistoryItem
from app.config import get_settings

router = APIRouter(prefix="/payments", tags=["Pagos"])
settings = get_settings()

ALLOWED_RECEIPT_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@router.get("/plans", response_model=list[PlanInfo])
async def get_plans():
    """Catálogo público de planes (Starter/Pro/Studio) con precios en colones."""
    return sinpe_service.get_plan_catalog()


@router.get("/sinpe-info")
async def get_sinpe_info():
    """Datos que el cliente necesita para hacer la transferencia SINPE Móvil."""
    return {
        "phone_number": settings.SINPE_PHONE_NUMBER,
        "owner_name": settings.SINPE_OWNER_NAME,
        "approval_sla": settings.SINPE_APPROVAL_SLA_TEXT,
        "instructions": (
            "Realiza tu pago por SINPE Móvil al número indicado, luego sube "
            "una captura del comprobante y selecciona el plan correspondiente. "
            "Tu membresía quedará en estado 'Pendiente de aprobación' hasta que "
            "un administrador la valide."
        ),
    }


@router.get("/history", response_model=list[SinpePaymentHistoryItem])
async def get_payment_history(user: AuthUser = Depends(get_current_user)):
    """Historial de comprobantes SINPE del cliente, con su estado actual."""
    return sinpe_service.list_payments_for_user(user.id)


@router.post(
    "/sinpe/upload-receipt",
    response_model=SinpePaymentCreateResponse,
    dependencies=[Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=10, window_seconds=60))],
)
async def upload_sinpe_receipt(
    plan: str = Form(...),
    receipt: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
):
    """El cliente sube la imagen del comprobante SINPE + el plan elegido."""
    if receipt.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(
            status_code=400, detail="El comprobante debe ser una imagen .jpg o .png"
        )

    receipt_url = await storage_service.upload_file(
        file=receipt,
        bucket="sinpe-receipts",
        path_prefix=f"{user.id}",
        allowed_extensions=storage_service.ALLOWED_RECEIPT_EXTENSIONS,
    )
    payment = sinpe_service.create_pending_payment(
        user_id=user.id, plan=plan, receipt_image_url=receipt_url
    )
    return SinpePaymentCreateResponse(**payment)
