from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config.settings import settings
from src.backend.services.drug_supply_chain.models import (
    DosageForm,
    DrugCategory,
    ExpiryTracking,
    Medicine,
    MovementType,
    OrderStatus,
    PurchaseOrder,
    StockLevel,
    StockMovement,
    StockoutPrediction,
    Supplier,
)

logger = logging.getLogger(__name__)


class DrugSupplyChainService:
    def __init__(self):
        self.moh_endpoint = settings.MOH_ENDPOINT

    # ------------------------------------------------------------------
    # Medicine catalog
    # ------------------------------------------------------------------
    async def create_medicine(self, session: AsyncSession, data: dict[str, Any]) -> Medicine:
        med = Medicine(
            name=data["name"],
            generic_name=data.get("generic_name"),
            category=DrugCategory(data["category"]),
            dosage_form=DosageForm(data["dosage_form"]),
            strength=data.get("strength"),
            manufacturer=data.get("manufacturer"),
            supplier_id=data.get("supplier_id"),
            is_essential_medicine=data.get("is_essential_medicine", False),
            is_controlled_substance=data.get("is_controlled_substance", False),
            requires_prescription=data.get("requires_prescription", True),
            unit_of_measure=data.get("unit_of_measure", "tablet"),
            reorder_level=data.get("reorder_level", 0),
            reorder_quantity=data.get("reorder_quantity", 0),
            unit_price_zmw=data.get("unit_price_zmw"),
            storage_conditions=data.get("storage_conditions"),
            description=data.get("description"),
            who_eml_listed=data.get("who_eml_listed", False),
            zambia_eml_listed=data.get("zambia_eml_listed", False),
            zambia_eml_level=data.get("zambia_eml_level"),
            hospital_id=data.get("hospital_id"),
        )
        session.add(med)
        await session.flush()
        return med

    async def search_medicines(
        self, session: AsyncSession, name: str | None = None,
        category: str | None = None, essential_only: bool = False,
        generic_name: str | None = None, limit: int = 100,
    ) -> list[Medicine]:
        query = select(Medicine).where(Medicine.is_active == True)
        if name:
            query = query.where(Medicine.name.ilike(f"%{name}%"))
        if category:
            query = query.where(Medicine.category == DrugCategory(category))
        if essential_only:
            query = query.where(Medicine.is_essential_medicine == True)
        if generic_name:
            query = query.where(Medicine.generic_name.ilike(f"%{generic_name}%"))
        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_medicine(self, session: AsyncSession, medicine_id: str) -> Medicine | None:
        result = await session.execute(select(Medicine).where(Medicine.id == medicine_id))
        return result.scalar_one_or_none()

    async def get_zambia_eml(self, session: AsyncSession) -> list[Medicine]:
        result = await session.execute(
            select(Medicine).where(Medicine.zambia_eml_listed == True)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------
    async def create_supplier(self, session: AsyncSession, data: dict[str, Any]) -> Supplier:
        supplier = Supplier(
            name=data["name"],
            contact_person=data.get("contact_person"),
            phone=data.get("phone"),
            email=data.get("email"),
            address=data.get("address"),
            license_number=data.get("license_number"),
            contract_start_date=data.get("contract_start_date"),
            contract_end_date=data.get("contract_end_date"),
            payment_terms=data.get("payment_terms"),
            lead_time_days=data.get("lead_time_days"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(supplier)
        await session.flush()
        return supplier

    async def list_suppliers(self, session: AsyncSession, active_only: bool = True) -> list[Supplier]:
        query = select(Supplier)
        if active_only:
            query = query.where(Supplier.is_active == True)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Stock management
    # ------------------------------------------------------------------
    async def add_stock(
        self, session: AsyncSession, medicine_id: str, quantity: int,
        batch_number: str, expiry_date: date | None = None,
        unit_cost: Decimal | None = None, location: str | None = None,
        reference_type: str | None = None, reference_id: str | None = None,
        performed_by: str | None = None, hospital_id: str | None = None,
    ) -> StockLevel:
        existing = await session.execute(
            select(StockLevel).where(
                StockLevel.medicine_id == medicine_id,
                StockLevel.batch_number == batch_number,
                StockLevel.is_deleted == False,
            )
        )
        stock_level = existing.scalar_one_or_none()
        if stock_level:
            stock_level.quantity += quantity
        else:
            stock_level = StockLevel(
                medicine_id=medicine_id,
                quantity=quantity,
                batch_number=batch_number,
                expiry_date=expiry_date,
                unit_cost_zmw=unit_cost,
                location=location,
                hospital_id=hospital_id,
            )
            session.add(stock_level)

        movement = StockMovement(
            medicine_id=medicine_id,
            movement_type=MovementType.receipt,
            quantity=quantity,
            batch_number=batch_number,
            expiry_date=expiry_date,
            unit_cost_zmw=unit_cost,
            total_cost_zmw=unit_cost * quantity if unit_cost else None,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
            hospital_id=hospital_id,
        )
        session.add(movement)

        if expiry_date:
            await self._track_expiry(session, medicine_id, batch_number, quantity, expiry_date, unit_cost, hospital_id)

        await session.flush()
        return stock_level

    async def dispense_stock(
        self, session: AsyncSession, medicine_id: str, quantity: int,
        batch_number: str | None = None, reference_type: str | None = None,
        reference_id: str | None = None, performed_by: str | None = None,
        hospital_id: str | None = None,
    ) -> StockLevel | None:
        query = select(StockLevel).where(
            StockLevel.medicine_id == medicine_id,
            StockLevel.is_deleted == False,
            StockLevel.quantity > 0,
        )
        if batch_number:
            query = query.where(StockLevel.batch_number == batch_number)
        query = query.order_by(StockLevel.expiry_date.asc().nulls_last())
        result = await session.execute(query)
        stock_levels = list(result.scalars().all())

        remaining = quantity
        for sl in stock_levels:
            if remaining <= 0:
                break
            dispense_qty = min(remaining, sl.quantity)
            sl.quantity -= dispense_qty
            remaining -= dispense_qty
            movement = StockMovement(
                medicine_id=medicine_id,
                movement_type=MovementType.dispensation,
                quantity=-dispense_qty,
                batch_number=sl.batch_number,
                unit_cost_zmw=sl.unit_cost_zmw,
                total_cost_zmw=sl.unit_cost_zmw * dispense_qty if sl.unit_cost_zmw else None,
                reference_type=reference_type,
                reference_id=reference_id,
                performed_by=performed_by,
                hospital_id=hospital_id,
            )
            session.add(movement)

        if remaining > 0:
            logger.warning("Insufficient stock for medicine %s. Short by %d", medicine_id, remaining)

        await session.flush()
        return stock_levels[0] if stock_levels else None

    async def transfer_stock(
        self, session: AsyncSession, medicine_id: str, quantity: int,
        batch_number: str, from_hospital: str, to_hospital: str,
        performed_by: str | None = None,
    ) -> tuple[StockMovement, StockMovement]:
        out_movement = StockMovement(
            medicine_id=medicine_id,
            movement_type=MovementType.transfer_out,
            quantity=-quantity,
            batch_number=batch_number,
            performed_by=performed_by,
            hospital_id=from_hospital,
            notes=f"Transfer to {to_hospital}",
        )
        session.add(out_movement)

        in_movement = StockMovement(
            medicine_id=medicine_id,
            movement_type=MovementType.transfer_in,
            quantity=quantity,
            batch_number=batch_number,
            performed_by=performed_by,
            hospital_id=to_hospital,
            notes=f"Transfer from {from_hospital}",
        )
        session.add(in_movement)
        await session.flush()
        return out_movement, in_movement

    async def get_stock_level(
        self, session: AsyncSession, medicine_id: str | None = None,
        hospital_id: str | None = None, near_expiry_days: int | None = None,
        low_stock_only: bool = False,
    ) -> list[dict]:
        query = select(
            StockLevel.medicine_id,
            Medicine.name,
            Medicine.generic_name,
            Medicine.category,
            Medicine.reorder_level,
            func.sum(StockLevel.quantity).label("total_quantity"),
            func.min(StockLevel.expiry_date).label("earliest_expiry"),
        ).join(Medicine, StockLevel.medicine_id == Medicine.id
        ).where(StockLevel.is_deleted == False)
        if medicine_id:
            query = query.where(StockLevel.medicine_id == medicine_id)
        if hospital_id:
            query = query.where(StockLevel.hospital_id == hospital_id)
        query = query.group_by(StockLevel.medicine_id, Medicine.name, Medicine.generic_name, Medicine.category, Medicine.reorder_level)
        result = await session.execute(query)
        rows = result.all()

        stock_data = []
        for row in rows:
            qty = row.total_quantity or 0
            is_low = qty <= (row.reorder_level or 0)
            is_near_expiry = False
            if row.earliest_expiry and near_expiry_days:
                is_near_expiry = (row.earliest_expiry - date.today()).days <= near_expiry_days
            if low_stock_only and not is_low:
                continue
            stock_data.append({
                "medicine_id": str(row.medicine_id),
                "name": row.name,
                "generic_name": row.generic_name,
                "category": row.category.value if row.category else None,
                "total_quantity": qty,
                "reorder_level": row.reorder_level,
                "is_low_stock": is_low,
                "earliest_expiry": row.earliest_expiry.isoformat() if row.earliest_expiry else None,
                "is_near_expiry": is_near_expiry,
            })
        return stock_data

    # ------------------------------------------------------------------
    # Purchase orders
    # ------------------------------------------------------------------
    async def create_purchase_order(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> PurchaseOrder:
        po = PurchaseOrder(
            order_number=data["order_number"],
            supplier_id=data["supplier_id"],
            order_date=data.get("order_date", date.today()),
            expected_delivery_date=data.get("expected_delivery_date"),
            items=json.dumps(data.get("items", [])),
            total_amount_zmw=data.get("total_amount_zmw"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(po)
        await session.flush()
        return po

    async def receive_purchase_order(
        self, session: AsyncSession, po_id: str, received_by: str,
    ) -> PurchaseOrder | None:
        result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
        po = result.scalar_one_or_none()
        if not po:
            return None
        po.status = OrderStatus.received
        po.received_date = date.today()
        await session.flush()

        items = json.loads(po.items or "[]")
        for item in items:
            await self.add_stock(
                session=session,
                medicine_id=item["medicine_id"],
                quantity=item["quantity"],
                batch_number=item.get("batch_number", f"PO-{po.order_number}"),
                expiry_date=item.get("expiry_date"),
                unit_cost=Decimal(str(item.get("unit_cost", 0))) if item.get("unit_cost") else None,
                reference_type="purchase_order",
                reference_id=str(po.id),
                performed_by=received_by,
                hospital_id=po.hospital_id,
            )
        return po

    async def list_purchase_orders(
        self, session: AsyncSession, status: str | None = None,
        supplier_id: str | None = None, limit: int = 100,
    ) -> list[PurchaseOrder]:
        query = select(PurchaseOrder)
        if status:
            query = query.where(PurchaseOrder.status == OrderStatus(status))
        if supplier_id:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)
        query = query.order_by(PurchaseOrder.order_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Expiry tracking
    # ------------------------------------------------------------------
    async def _track_expiry(
        self, session: AsyncSession, medicine_id: str, batch_number: str,
        quantity: int, expiry_date: date, unit_cost: Decimal | None = None,
        hospital_id: str | None = None,
    ) -> None:
        days_until = (expiry_date - date.today()).days
        tracking = ExpiryTracking(
            medicine_id=medicine_id,
            medicine_name="",
            batch_number=batch_number,
            expiry_date=expiry_date,
            quantity_at_risk=quantity,
            unit_cost_zmw=unit_cost,
            total_value_at_risk_zmw=unit_cost * quantity if unit_cost else None,
            days_until_expiry=days_until,
            status="active" if days_until > 0 else "expired",
            hospital_id=hospital_id,
        )
        session.add(tracking)

    async def get_expiring_stock(
        self, session: AsyncSession, within_days: int = 90,
        hospital_id: str | None = None,
    ) -> list[dict]:
        today = date.today()
        cutoff = today + timedelta(days=within_days)
        query = select(
            ExpiryTracking.medicine_id,
            Medicine.name,
            ExpiryTracking.batch_number,
            ExpiryTracking.expiry_date,
            ExpiryTracking.quantity_at_risk,
            ExpiryTracking.total_value_at_risk_zmw,
            ExpiryTracking.days_until_expiry,
        ).join(Medicine, ExpiryTracking.medicine_id == Medicine.id
        ).where(
            ExpiryTracking.expiry_date <= cutoff,
            ExpiryTracking.expiry_date > today,
            ExpiryTracking.disposed == False,
        )
        if hospital_id:
            query = query.where(ExpiryTracking.hospital_id == hospital_id)
        query = query.order_by(ExpiryTracking.expiry_date.asc())
        result = await session.execute(query)
        rows = result.all()
        return [
            {
                "medicine_id": str(r.medicine_id),
                "name": r.name,
                "batch_number": r.batch_number,
                "expiry_date": r.expiry_date.isoformat(),
                "quantity": r.quantity_at_risk,
                "value_zmw": float(r.total_value_at_risk_zmw) if r.total_value_at_risk_zmw else 0,
                "days_remaining": r.days_until_expiry,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Stock-out prediction (time-series based)
    # ------------------------------------------------------------------
    async def predict_stockouts(
        self, session: AsyncSession, hospital_id: str | None = None,
    ) -> list[StockoutPrediction]:
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        medicines_query = select(Medicine.id, Medicine.name, Medicine.reorder_level, Medicine.reorder_quantity)
        if hospital_id:
            meds_result = await session.execute(medicines_query)
        else:
            meds_result = await session.execute(medicines_query)
        medicines = meds_result.all()

        predictions = []
        for med_id, med_name, reorder_level, reorder_qty in medicines:
            total_stock = await session.execute(
                select(func.coalesce(func.sum(StockLevel.quantity), 0)).where(
                    StockLevel.medicine_id == med_id,
                    StockLevel.is_deleted == False,
                )
            )
            current_stock = total_stock.scalar() or 0

            movements_result = await session.execute(
                select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                    StockMovement.medicine_id == med_id,
                    StockMovement.movement_type == MovementType.dispensation,
                    StockMovement.movement_date >= thirty_days_ago,
                )
            )
            total_dispensed = abs(movements_result.scalar() or 0)
            daily_rate = total_dispensed / 30.0 if total_dispensed > 0 else 0

            days_until = int(current_stock / daily_rate) if daily_rate > 0 else 999
            predicted_date = today + timedelta(days=days_until) if days_until < 365 else None

            if daily_rate > 0 and days_until <= 90:
                if days_until <= 0:
                    risk = "critical"
                elif days_until <= 14:
                    risk = "high"
                elif days_until <= 30:
                    risk = "medium"
                else:
                    risk = "low"

                pred = StockoutPrediction(
                    medicine_id=med_id,
                    medicine_name=med_name,
                    current_stock=current_stock,
                    daily_consumption_rate=round(daily_rate, 2),
                    days_until_stockout=days_until,
                    predicted_stockout_date=predicted_date,
                    confidence_score=0.85 if daily_rate > 1 else 0.6,
                    recommended_order_quantity=max(reorder_qty, int(daily_rate * 60)),
                    lead_time_days=14,
                    risk_level=risk,
                    prediction_date=today,
                    hospital_id=hospital_id,
                )
                predictions.append(pred)

        for pred in predictions:
            session.add(pred)
        await session.flush()
        return predictions

    async def get_stockout_predictions(
        self, session: AsyncSession, risk_level: str | None = None,
        hospital_id: str | None = None, limit: int = 50,
    ) -> list[StockoutPrediction]:
        today = date.today()
        query = select(StockoutPrediction).where(
            StockoutPrediction.prediction_date == today,
        )
        if risk_level:
            query = query.where(StockoutPrediction.risk_level == risk_level)
        if hospital_id:
            query = query.where(StockoutPrediction.hospital_id == hospital_id)
        query = query.order_by(StockoutPrediction.days_until_stockout.asc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Dashboard & reporting
    # ------------------------------------------------------------------
    async def get_dashboard(self, session: AsyncSession, hospital_id: str | None = None) -> dict[str, Any]:
        today = date.today()
        month_start = today.replace(day=1)

        total_medicines = (await session.execute(
            select(func.count(Medicine.id)).where(Medicine.is_active == True)
        )).scalar() or 0

        stock_data = await self.get_stock_level(session, hospital_id=hospital_id)
        low_stock = sum(1 for s in stock_data if s["is_low_stock"])
        total_value_result = await session.execute(
            select(func.coalesce(func.sum(StockLevel.quantity * StockLevel.unit_cost_zmw), 0)).where(
                StockLevel.is_deleted == False,
            )
        )
        total_value = total_value_result.scalar() or 0

        monthly_movements = (await session.execute(
            select(func.count(StockMovement.id)).where(
                StockMovement.movement_date >= month_start,
            )
        )).scalar() or 0

        expiring = await self.get_expiring_stock(session, within_days=90, hospital_id=hospital_id)

        critical_predictions = await self.get_stockout_predictions(session, risk_level="critical", hospital_id=hospital_id)

        return {
            "total_medicines": total_medicines,
            "total_stock_items": len(stock_data),
            "low_stock_items": low_stock,
            "total_inventory_value_zmw": float(total_value),
            "monthly_movements": monthly_movements,
            "expiring_within_90_days": len(expiring),
            "critical_stockout_risk": len(critical_predictions),
        }

    async def generate_moh_report(
        self, session: AsyncSession, hospital_id: str | None = None,
    ) -> dict[str, Any]:
        today = date.today()
        month_start = today.replace(day=1)
        query = select(
            Medicine.category,
            func.sum(StockLevel.quantity).label("total_stock"),
            func.count(Medicine.id).label("medicine_count"),
        ).join(StockLevel, Medicine.id == StockLevel.medicine_id
        ).where(StockLevel.is_deleted == False)
        if hospital_id:
            query = query.where(StockLevel.hospital_id == hospital_id)
        query = query.group_by(Medicine.category)
        result = await session.execute(query)
        rows = result.all()

        category_data = {}
        for r in rows:
            category_data[r.category.value] = {
                "medicine_count": r.medicine_count,
                "total_stock": r.total_stock,
            }

        stockout_data = await self.get_stockout_predictions(session, hospital_id=hospital_id)
        critical_items = [s for s in stockout_data if s.risk_level in ("critical", "high")]

        return {
            "report_date": today.isoformat(),
            "hospital_id": hospital_id,
            "stock_by_category": category_data,
            "total_categories": len(category_data),
            "critical_stockout_items": len(critical_items),
            "stockout_details": [
                {
                    "medicine": s.medicine_name,
                    "current_stock": s.current_stock,
                    "days_remaining": s.days_until_stockout,
                    "risk": s.risk_level,
                }
                for s in critical_items[:20]
            ],
        }

    async def submit_to_moh(self, report: dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.moh_endpoint}/api/drug-supply/reports",
                    json=report,
                )
                return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Failed to submit report to MoH: %s", e)
            return False


drug_supply_service = DrugSupplyChainService()
