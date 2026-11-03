from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.pharmacy.models import (
    Dispensation,
    DispensationStatus,
    DrugInteraction,
    FormularyItem,
    InteractionSeverity,
    PharmacyInventory,
    Prescription,
    PrescriptionItem,
    PrescriptionStatus,
)

logger = logging.getLogger(__name__)


class PharmacyService:
    # ------------------------------------------------------------------
    # Formulary
    # ------------------------------------------------------------------
    async def get_formulary(
        self, session: AsyncSession, essential_only: bool = False,
        zambia_eml_only: bool = False, search: str | None = None,
    ) -> list[FormularyItem]:
        query = select(FormularyItem).where(FormularyItem.is_active == True)
        if essential_only:
            query = query.where(FormularyItem.is_essential_medication == True)
        if zambia_eml_only:
            query = query.where(FormularyItem.zambia_eml_listed == True)
        if search:
            query = query.where(
                FormularyItem.medicine_name.ilike(f"%{search}%") |
                FormularyItem.generic_name.ilike(f"%{search}%")
            )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def add_formulary_item(self, session: AsyncSession, data: dict[str, Any]) -> FormularyItem:
        item = FormularyItem(
            medicine_name=data["medicine_name"],
            generic_name=data.get("generic_name"),
            dosage_form=data["dosage_form"],
            strength=data.get("strength"),
            therapeutic_class=data.get("therapeutic_class"),
            is_controlled=data.get("is_controlled", False),
            requires_prescription=data.get("requires_prescription", True),
            is_essential_medication=data.get("is_essential_medication", False),
            zambia_eml_listed=data.get("zambia_eml_listed", False),
            max_daily_dosage=data.get("max_daily_dosage"),
            common_side_effects=data.get("common_side_effects"),
            contraindications=data.get("contraindications"),
            unit_price_zmw=data.get("unit_price_zmw"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(item)
        await session.flush()
        return item

    # ------------------------------------------------------------------
    # Prescriptions
    # ------------------------------------------------------------------
    async def create_prescription(self, session: AsyncSession, data: dict[str, Any]) -> Prescription:
        rx = Prescription(
            prescription_number=data.get("prescription_number", f"RX-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
            patient_id=data["patient_id"],
            encounter_id=data.get("encounter_id"),
            prescribing_provider=data["prescribing_provider"],
            prescribing_provider_id=data.get("prescribing_provider_id"),
            diagnosis=data.get("diagnosis"),
            prescription_date=data.get("prescription_date", date.today()),
            expiry_date=data.get("expiry_date"),
            is_emergency=data.get("is_emergency", False),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(rx)
        await session.flush()

        for item_data in data.get("items", []):
            item = PrescriptionItem(
                prescription_id=rx.id,
                medicine_name=item_data["medicine_name"],
                generic_name=item_data.get("generic_name"),
                dosage=item_data["dosage"],
                frequency=item_data["frequency"],
                route=item_data.get("route", "oral"),
                duration_days=item_data.get("duration_days"),
                quantity=item_data["quantity"],
                refills=item_data.get("refills", 0),
                instructions=item_data.get("instructions"),
                substitution_allowed=item_data.get("substitution_allowed", True),
                hospital_id=data.get("hospital_id"),
            )
            session.add(item)

        await session.flush()
        return rx

    async def get_prescription(self, session: AsyncSession, rx_id: str) -> Prescription | None:
        result = await session.execute(
            select(Prescription).where(Prescription.id == rx_id)
        )
        return result.scalar_one_or_none()

    async def search_prescriptions(
        self, session: AsyncSession, patient_id: str | None = None,
        provider_id: str | None = None, status: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
        limit: int = 100,
    ) -> list[Prescription]:
        query = select(Prescription)
        if patient_id:
            query = query.where(Prescription.patient_id == patient_id)
        if provider_id:
            query = query.where(Prescription.prescribing_provider_id == provider_id)
        if status:
            query = query.where(Prescription.status == PrescriptionStatus(status))
        if date_from:
            query = query.where(Prescription.prescription_date >= date_from)
        if date_to:
            query = query.where(Prescription.prescription_date <= date_to)
        query = query.order_by(Prescription.prescription_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def cancel_prescription(
        self, session: AsyncSession, rx_id: str, reason: str | None = None,
    ) -> Prescription | None:
        rx = await self.get_prescription(session, rx_id)
        if not rx:
            return None
        rx.status = PrescriptionStatus.cancelled
        if reason:
            rx.notes = (rx.notes or "") + f"\nCancelled: {reason}"
        await session.flush()
        return rx

    # ------------------------------------------------------------------
    # Dispensing workflow
    # ------------------------------------------------------------------
    async def dispense(
        self, session: AsyncSession, data: dict[str, Any],
    ) -> Dispensation:
        rx_id = data["prescription_id"]
        rx = await self.get_prescription(session, rx_id)
        if not rx:
            raise ValueError("Prescription not found")
        if rx.status == PrescriptionStatus.cancelled:
            raise ValueError("Cannot dispense cancelled prescription")
        if rx.status == PrescriptionStatus.expired:
            raise ValueError("Cannot dispense expired prescription")

        total_cost = Decimal("0.00")
        dispensation = Dispensation(
            prescription_id=rx_id,
            prescription_item_id=data.get("prescription_item_id"),
            medicine_name=data["medicine_name"],
            batch_number=data.get("batch_number"),
            quantity_dispensed=data["quantity_dispensed"],
            dispensation_date=datetime.now(timezone.utc),
            dispensed_by=data["dispensed_by"],
            unit_price_zmw=data.get("unit_price_zmw"),
            total_price_zmw=data.get("unit_price_zmw", 0) * data["quantity_dispensed"] if data.get("unit_price_zmw") else None,
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(dispensation)

        rx.status = PrescriptionStatus.dispensed
        await session.flush()
        return dispensation

    async def verify_dispensation(
        self, session: AsyncSession, dispensation_id: str, verified_by: str,
    ) -> Dispensation | None:
        result = await session.execute(
            select(Dispensation).where(Dispensation.id == dispensation_id)
        )
        disp = result.scalar_one_or_none()
        if not disp:
            return None
        disp.status = DispensationStatus.verified
        disp.verified_by = verified_by
        disp.verified_at = datetime.now(timezone.utc)
        await session.flush()
        return disp

    # ------------------------------------------------------------------
    # Drug interaction checking
    # ------------------------------------------------------------------
    async def check_interactions(
        self, session: AsyncSession, drug_names: list[str],
    ) -> list[dict[str, Any]]:
        if len(drug_names) < 2:
            return []
        interactions: list[dict[str, Any]] = []
        for i in range(len(drug_names)):
            for j in range(i + 1, len(drug_names)):
                result = await session.execute(
                    select(DrugInteraction).where(
                        ((DrugInteraction.drug_a.ilike(drug_names[i])) & (DrugInteraction.drug_b.ilike(drug_names[j]))) |
                        ((DrugInteraction.drug_a.ilike(drug_names[j])) & (DrugInteraction.drug_b.ilike(drug_names[i])))
                    )
                )
                for interaction in result.scalars().all():
                    interactions.append({
                        "drug_a": drug_names[i],
                        "drug_b": drug_names[j],
                        "severity": interaction.severity.value,
                        "mechanism": interaction.mechanism,
                        "clinical_effect": interaction.clinical_effect,
                        "recommendation": interaction.recommendation,
                    })
        return interactions

    async def add_interaction(
        self, session: AsyncSession, data: dict[str, Any],
    ) -> DrugInteraction:
        interaction = DrugInteraction(
            drug_a=data["drug_a"],
            drug_b=data["drug_b"],
            severity=InteractionSeverity(data["severity"]),
            mechanism=data.get("mechanism"),
            clinical_effect=data.get("clinical_effect"),
            recommendation=data.get("recommendation"),
            evidence_level=data.get("evidence_level"),
            source=data.get("source"),
        )
        session.add(interaction)
        await session.flush()
        return interaction

    async def check_prescription_interactions(
        self, session: AsyncSession, prescription_id: str,
    ) -> list[dict[str, Any]]:
        rx = await self.get_prescription(session, prescription_id)
        if not rx or not rx.items:
            return []
        drug_names = [item.medicine_name for item in rx.items]
        return await self.check_interactions(session, drug_names)

    # ------------------------------------------------------------------
    # Zambia Essential Medicines List integration
    # ------------------------------------------------------------------
    async def get_zambia_eml(self, session: AsyncSession) -> list[FormularyItem]:
        result = await session.execute(
            select(FormularyItem).where(
                FormularyItem.zambia_eml_listed == True,
                FormularyItem.is_active == True,
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Inventory (local pharmacy inventory)
    # ------------------------------------------------------------------
    async def get_inventory(
        self, session: AsyncSession, low_stock_only: bool = False,
        near_expiry_days: int | None = None,
    ) -> list[PharmacyInventory]:
        query = select(PharmacyInventory).where(PharmacyInventory.is_active == True)
        if low_stock_only:
            query = query.where(PharmacyInventory.quantity <= PharmacyInventory.reorder_level)
        if near_expiry_days:
            from datetime import timedelta
            threshold = date.today() + timedelta(days=near_expiry_days)
            query = query.where(PharmacyInventory.expiry_date <= threshold)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def adjust_inventory(
        self, session: AsyncSession, inventory_id: str, quantity_change: int,
        reason: str | None = None,
    ) -> PharmacyInventory | None:
        result = await session.execute(
            select(PharmacyInventory).where(PharmacyInventory.id == inventory_id)
        )
        inv = result.scalar_one_or_none()
        if not inv:
            return None
        inv.quantity += quantity_change
        await session.flush()
        return inv


pharmacy_service = PharmacyService()
