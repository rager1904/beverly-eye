"""Patient flow and journey tracking for UbuntuCare.

A *journey* is the container for one patient visit. Each *step* is a
service-point visit / queue ticket (registration, triage, consultation,
laboratory, pharmacy, ward, ...). Routing a patient completes the current
step and opens the next one, so the full care pathway is preserved as an
auditable timeline.
"""

from .models import JourneyStep, PatientJourney
from .services import JourneyService

__all__ = ["PatientJourney", "JourneyStep", "JourneyService"]
