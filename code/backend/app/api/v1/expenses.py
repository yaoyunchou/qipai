from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import delete, func, select

from app.core.deps import CurrentUser, DbSession
from app.models import (
    ExpenseApprovePermission,
    ExpenseApproverStatus,
    ExpenseClaim,
    ExpenseClaimApprover,
    ExpenseClaimAttachment,
    ExpenseClaimStatus,
    SysUser,
    UserRole,
)
from app.schemas.expense import (
    ApprovePermissionOut,
    ApprovePermissionUpdate,
    ApproverAction,
    ApproverRecordOut,
    AttachmentOut,
    ExpenseClaimOut,
    ExpenseCreate,
    ExpenseReportSummary,
    SelectableApproverOut,
)
from app.services.order_no import generate_order_no

router = APIRouter(prefix="/expenses", tags=["expenses"])

MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024


def _generate_claim_no() -> str:
    return f"BX{generate_order_no()[2:]}"


def _can_manage_permissions(user: SysUser) -> bool:
    return user.role in (UserRole.ADMIN, UserRole.SHAREHOLDER)


def _recalc_claim_status(claim: ExpenseClaim, approvers: list[ExpenseClaimApprover]) -> None:
    if any(a.status == ExpenseApproverStatus.REJECTED for a in approvers):
        claim.status = ExpenseClaimStatus.REJECTED
        return
    active = [a for a in approvers if a.status != ExpenseApproverStatus.SKIPPED]
    if not active:
        claim.status = ExpenseClaimStatus.PENDING
        return
    if all(a.status == ExpenseApproverStatus.APPROVED for a in active):
        claim.status = ExpenseClaimStatus.APPROVED
    else:
        claim.status = ExpenseClaimStatus.PENDING


def _to_out(claim: ExpenseClaim, db) -> ExpenseClaimOut:
    applicant = db.get(SysUser, claim.applicant_id)
    attachments = db.scalars(
        select(ExpenseClaimAttachment).where(ExpenseClaimAttachment.claim_id == claim.id)
    ).all()
    approver_rows = db.scalars(
        select(ExpenseClaimApprover)
        .where(ExpenseClaimApprover.claim_id == claim.id)
        .order_by(ExpenseClaimApprover.id)
    ).all()
    approvers: list[ApproverRecordOut] = []
    for row in approver_rows:
        approver = db.get(SysUser, row.approver_id)
        approvers.append(
            ApproverRecordOut(
                id=row.id,
                approver_id=row.approver_id,
                approver_name=approver.display_name if approver else None,
                status=row.status,
                comment=row.comment,
                acted_at=row.acted_at,
            )
        )
    return ExpenseClaimOut(
        id=claim.id,
        claim_no=claim.claim_no,
        applicant_id=claim.applicant_id,
        applicant_name=applicant.display_name if applicant else None,
        amount=claim.amount,
        remark=claim.remark,
        status=claim.status,
        submitted_at=claim.submitted_at,
        attachments=[AttachmentOut.model_validate(a) for a in attachments],
        approvers=approvers,
    )


def _visible_claim_ids(db, user: SysUser) -> set[int]:
    own = db.scalars(
        select(ExpenseClaim.id).where(ExpenseClaim.applicant_id == user.id)
    ).all()
    assigned = db.scalars(
        select(ExpenseClaimApprover.claim_id).where(ExpenseClaimApprover.approver_id == user.id)
    ).all()
    return set(own) | set(assigned)


def _ensure_visible(claim_id: int, user: SysUser, db) -> ExpenseClaim:
    claim = db.get(ExpenseClaim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="报销单不存在")
    if claim.id not in _visible_claim_ids(db, user):
        raise HTTPException(status_code=403, detail="无权查看该报销单")
    return claim


def _parse_range(period: str, start: date | None) -> tuple[datetime, datetime, str, str]:
    today = date.today()
    if period == "day":
        d = start or today
        s = datetime.combine(d, datetime.min.time())
        e = s + timedelta(days=1)
        return s, e, d.isoformat(), d.isoformat()
    if period == "week":
        d = start or today
        s = datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time())
        e = s + timedelta(days=7)
        return s, e, s.date().isoformat(), (e.date() - timedelta(days=1)).isoformat()
    if period == "month":
        d = start or today
        s = datetime.combine(d.replace(day=1), datetime.min.time())
        if d.month == 12:
            e = datetime(d.year + 1, 1, 1)
        else:
            e = datetime(d.year, d.month + 1, 1)
        return s, e, s.date().isoformat(), (e.date() - timedelta(days=1)).isoformat()
    raise HTTPException(status_code=400, detail="period 须为 day|week|month")


@router.get("/selectable-approvers", response_model=list[SelectableApproverOut])
def list_selectable_approvers(db: DbSession, user: CurrentUser):
    permitted_ids = db.scalars(select(ExpenseApprovePermission.user_id)).all()
    if not permitted_ids:
        return []
    users = db.scalars(
        select(SysUser)
        .where(
            SysUser.id.in_(permitted_ids),
            SysUser.is_enabled.is_(True),
            SysUser.id != user.id,
            SysUser.role.in_([UserRole.MANAGER, UserRole.SHAREHOLDER, UserRole.ADMIN]),
        )
        .order_by(SysUser.id)
    ).all()
    return [
        SelectableApproverOut(id=u.id, display_name=u.display_name, role=u.role.value)
        for u in users
    ]


@router.get("/approve-permissions", response_model=list[ApprovePermissionOut])
def list_approve_permissions(db: DbSession, user: CurrentUser):
    if not _can_manage_permissions(user):
        raise HTTPException(status_code=403, detail="仅超管或股东可管理审批授权")
    permitted = set(db.scalars(select(ExpenseApprovePermission.user_id)).all())
    users = db.scalars(
        select(SysUser)
        .where(
            SysUser.is_enabled.is_(True),
            SysUser.role.in_([UserRole.MANAGER, UserRole.SHAREHOLDER, UserRole.ADMIN]),
        )
        .order_by(SysUser.id)
    ).all()
    return [
        ApprovePermissionOut(
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            role=u.role.value,
            can_approve=u.id in permitted,
        )
        for u in users
    ]


@router.put("/approve-permissions", response_model=list[ApprovePermissionOut])
def update_approve_permissions(body: ApprovePermissionUpdate, db: DbSession, user: CurrentUser):
    if not _can_manage_permissions(user):
        raise HTTPException(status_code=403, detail="仅超管或股东可管理审批授权")
    valid_users = db.scalars(
        select(SysUser.id).where(
            SysUser.id.in_(body.user_ids),
            SysUser.is_enabled.is_(True),
            SysUser.role.in_([UserRole.MANAGER, UserRole.SHAREHOLDER, UserRole.ADMIN]),
        )
    ).all()
    valid_set = set(valid_users)
    db.execute(delete(ExpenseApprovePermission))
    for uid in valid_set:
        db.add(ExpenseApprovePermission(user_id=uid, granted_by=user.id))
    db.commit()
    return list_approve_permissions(db, user)


@router.get("", response_model=list[ExpenseClaimOut])
def list_expenses(
    db: DbSession,
    user: CurrentUser,
    scope: str = Query("all", pattern="^(all|mine|pending)$"),
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(50, le=200),
):
    visible = _visible_claim_ids(db, user)
    if not visible:
        return []
    q = (
        select(ExpenseClaim)
        .where(ExpenseClaim.id.in_(visible))
        .order_by(ExpenseClaim.submitted_at.desc())
        .limit(limit)
    )
    if scope == "mine":
        q = q.where(ExpenseClaim.applicant_id == user.id)
    elif scope == "pending":
        pending_claim_ids = db.scalars(
            select(ExpenseClaimApprover.claim_id).where(
                ExpenseClaimApprover.approver_id == user.id,
                ExpenseClaimApprover.status == ExpenseApproverStatus.PENDING,
            )
        ).all()
        q = q.where(
            ExpenseClaim.id.in_(pending_claim_ids),
            ExpenseClaim.status == ExpenseClaimStatus.PENDING,
        )
    if start:
        q = q.where(ExpenseClaim.submitted_at >= datetime.combine(start, datetime.min.time()))
    if end:
        q = q.where(
            ExpenseClaim.submitted_at < datetime.combine(end + timedelta(days=1), datetime.min.time())
        )
    claims = db.scalars(q).all()
    return [_to_out(c, db) for c in claims]


@router.post("", response_model=ExpenseClaimOut, status_code=status.HTTP_201_CREATED)
def create_expense(body: ExpenseCreate, db: DbSession, user: CurrentUser):
    if len(body.attachments) > MAX_ATTACHMENTS:
        raise HTTPException(status_code=400, detail=f"最多上传 {MAX_ATTACHMENTS} 个附件")
    for att in body.attachments:
        raw = att.data_base64
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        try:
            import base64

            size = len(base64.b64decode(raw, validate=True))
        except Exception:
            raise HTTPException(status_code=400, detail="附件格式无效")
        if size > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=400, detail="单个附件不能超过 3MB")

    permitted = set(db.scalars(select(ExpenseApprovePermission.user_id)).all())
    approver_ids = list(dict.fromkeys(body.approver_ids))
    for aid in approver_ids:
        if aid not in permitted:
            raise HTTPException(status_code=400, detail="所选审批人未获授权")
        if aid == user.id:
            raise HTTPException(status_code=400, detail="不能选择自己为审批人")
    approvers = db.scalars(
        select(SysUser).where(
            SysUser.id.in_(approver_ids),
            SysUser.is_enabled.is_(True),
        )
    ).all()
    if len(approvers) != len(approver_ids):
        raise HTTPException(status_code=400, detail="审批人不存在或已禁用")

    claim = ExpenseClaim(
        claim_no=_generate_claim_no(),
        applicant_id=user.id,
        amount=body.amount,
        remark=body.remark,
        status=ExpenseClaimStatus.PENDING,
        submitted_at=datetime.now(),
    )
    db.add(claim)
    db.flush()

    for att in body.attachments:
        raw = att.data_base64
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        db.add(
            ExpenseClaimAttachment(
                claim_id=claim.id,
                filename=att.filename,
                content_type=att.content_type,
                data_base64=raw,
            )
        )
    for aid in approver_ids:
        db.add(
            ExpenseClaimApprover(
                claim_id=claim.id,
                approver_id=aid,
                status=ExpenseApproverStatus.PENDING,
            )
        )
    db.commit()
    db.refresh(claim)
    return _to_out(claim, db)


@router.get("/reports/summary", response_model=ExpenseReportSummary)
def expense_report_summary(
    db: DbSession,
    user: CurrentUser,
    period: str = Query("day", pattern="^(day|week|month)$"),
    start: date | None = None,
):
    s, e, start_str, end_str = _parse_range(period, start)
    q = select(
        func.count(ExpenseClaim.id),
        func.coalesce(func.sum(ExpenseClaim.amount), 0),
    ).where(
        ExpenseClaim.status == ExpenseClaimStatus.APPROVED,
        ExpenseClaim.submitted_at >= s,
        ExpenseClaim.submitted_at < e,
    )
    if user.role == UserRole.CASHIER:
        q = q.where(ExpenseClaim.applicant_id == user.id)
    row = db.execute(q).one()
    return ExpenseReportSummary(
        period=period,
        start_date=start_str,
        end_date=end_str,
        claim_count=int(row[0] or 0),
        amount_total=Decimal(str(row[1])),
    )


@router.get("/reports/export")
def expense_report_export(
    db: DbSession,
    user: CurrentUser,
    period: str = Query("day", pattern="^(day|week|month)$"),
    start: date | None = None,
):
    if user.role == UserRole.SHAREHOLDER:
        raise HTTPException(status_code=403, detail="股东仅可查看汇总报表")
    s, e, start_str, end_str = _parse_range(period, start)

    q = (
        select(ExpenseClaim)
        .where(
            ExpenseClaim.status == ExpenseClaimStatus.APPROVED,
            ExpenseClaim.submitted_at >= s,
            ExpenseClaim.submitted_at < e,
        )
        .order_by(ExpenseClaim.submitted_at.desc())
    )
    if user.role == UserRole.CASHIER:
        q = q.where(ExpenseClaim.applicant_id == user.id)

    claims = db.scalars(q).all()

    wb = Workbook()
    ws_sum = wb.active
    ws_sum.title = "汇总"
    total = sum(c.amount for c in claims)
    ws_sum.append(["统计周期", f"{start_str} ~ {end_str}"])
    ws_sum.append(["报表类型", {"day": "日报", "week": "周报", "month": "月报"}[period]])
    ws_sum.append(["已完成报销笔数", len(claims)])
    ws_sum.append(["报销总金额", float(total)])

    ws_detail = wb.create_sheet("明细")
    ws_detail.append(
        ["单号", "申请人", "金额", "申请备注", "提交时间", "审批人", "审批意见", "审批时间"]
    )
    for claim in claims:
        applicant = db.get(SysUser, claim.applicant_id)
        approver_rows = db.scalars(
            select(ExpenseClaimApprover)
            .where(
                ExpenseClaimApprover.claim_id == claim.id,
                ExpenseClaimApprover.status.in_(
                    [ExpenseApproverStatus.APPROVED, ExpenseApproverStatus.SKIPPED]
                ),
            )
            .order_by(ExpenseClaimApprover.id)
        ).all()
        if not approver_rows:
            ws_detail.append(
                [
                    claim.claim_no,
                    applicant.display_name if applicant else "",
                    float(claim.amount),
                    claim.remark or "",
                    claim.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "",
                    "",
                    "",
                ]
            )
        else:
            for i, ar in enumerate(approver_rows):
                approver = db.get(SysUser, ar.approver_id)
                ws_detail.append(
                    [
                        claim.claim_no if i == 0 else "",
                        applicant.display_name if applicant and i == 0 else "",
                        float(claim.amount) if i == 0 else "",
                        claim.remark or "" if i == 0 else "",
                        claim.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if i == 0 else "",
                        approver.display_name if approver else "",
                        ar.comment or "",
                        ar.acted_at.strftime("%Y-%m-%d %H:%M:%S") if ar.acted_at else "",
                    ]
                )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"expense_{period}_{start_str}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{claim_id}", response_model=ExpenseClaimOut)
def get_expense(claim_id: int, db: DbSession, user: CurrentUser):
    claim = _ensure_visible(claim_id, user, db)
    return _to_out(claim, db)


def _do_approver_action(
    claim_id: int,
    user: CurrentUser,
    db: DbSession,
    action: ExpenseApproverStatus,
    comment: str | None,
) -> ExpenseClaimOut:
    claim = _ensure_visible(claim_id, user, db)
    if claim.status != ExpenseClaimStatus.PENDING:
        raise HTTPException(status_code=400, detail="该报销单已结束审批")
    row = db.scalar(
        select(ExpenseClaimApprover).where(
            ExpenseClaimApprover.claim_id == claim_id,
            ExpenseClaimApprover.approver_id == user.id,
        )
    )
    if not row:
        raise HTTPException(status_code=403, detail="您不是该单的审批人")
    if row.status != ExpenseApproverStatus.PENDING:
        raise HTTPException(status_code=400, detail="您已处理过该审批")
    if action in (ExpenseApproverStatus.APPROVED, ExpenseApproverStatus.REJECTED) and not comment:
        raise HTTPException(status_code=400, detail="请填写审批意见")

    row.status = action
    row.comment = comment
    row.acted_at = datetime.now()

    all_approvers = db.scalars(
        select(ExpenseClaimApprover).where(ExpenseClaimApprover.claim_id == claim_id)
    ).all()
    _recalc_claim_status(claim, all_approvers)
    db.commit()
    db.refresh(claim)
    return _to_out(claim, db)


@router.post("/{claim_id}/approve", response_model=ExpenseClaimOut)
def approve_expense(claim_id: int, body: ApproverAction, db: DbSession, user: CurrentUser):
    return _do_approver_action(
        claim_id, user, db, ExpenseApproverStatus.APPROVED, body.comment.strip()
    )


@router.post("/{claim_id}/reject", response_model=ExpenseClaimOut)
def reject_expense(claim_id: int, body: ApproverAction, db: DbSession, user: CurrentUser):
    return _do_approver_action(
        claim_id, user, db, ExpenseApproverStatus.REJECTED, body.comment.strip()
    )


@router.post("/{claim_id}/skip", response_model=ExpenseClaimOut)
def skip_expense(claim_id: int, db: DbSession, user: CurrentUser):
    return _do_approver_action(claim_id, user, db, ExpenseApproverStatus.SKIPPED, "不参与审批")
