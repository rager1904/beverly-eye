from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FAQEntry:
    question: str
    answer: str
    category: str
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    translations: Dict[str, str] = field(default_factory=dict)
    requires_professional: bool = False
    region_specific: Optional[str] = None


FAQ_DATABASE: List[FAQEntry] = [
    # ---- Malaria ----
    FAQEntry(
        question="What are the symptoms of malaria?",
        answer="Common symptoms of malaria include fever, chills, headache, muscle pain, and sweating. In Zambia, if you have fever with any of these symptoms, go to your nearest health facility for a malaria test (RDT or microscopy). Treatment is free at public health facilities. Malaria can be dangerous, especially for pregnant women and children under 5.",
        category="malaria",
        keywords=["malaria", "fever", "chills", "symptoms", "headache", "sweating"],
        translations={
            "bem": "Ububilo bwa malaria: ukubaba, imitwe, ubusunta, no kulwelela. Nga mwalandilila pa cibinda mupimishe.",
            "ny": "Zizindikiro za malaria: kutentha thupi, kuzizira, mutu, kupweteka minofu, thukuta. Pitani ku chipatala kukayezetsa.",
            "to": "Matala a malaria: kulila umutwe, kukala, kusisimuka, kubaba mikobili.",
        },
        region_specific="Zambia - endemic area, seasonal transmission",
    ),
    FAQEntry(
        question="How is malaria treated in Zambia?",
        answer="The first-line treatment for uncomplicated malaria in Zambia is Artemether-Lumefantrine (AL), also known as Coartem. This is a 3-day course of twice-daily tablets. Treatment is free at all public health facilities. For severe malaria, injectable artesunate is used. Always complete the full course even if you feel better.",
        category="malaria",
        keywords=["treatment", "malaria", "coartem", "artemether", "lumefantrine", "artesunate"],
        translations={
            "bem": "Umuti wa malaria ni AL (Coartem). Mule ya pa makashita yonse. Nga mwamina bwino, mule yafwa.",
        },
    ),
    # ---- HIV ----
    FAQEntry(
        question="Where can I get HIV testing in Zambia?",
        answer="HIV testing is available at all public health facilities, clinics, and hospitals in Zambia. Testing is free and confidential. You can also access testing at mobile clinics and during community health campaigns. Results are available within 20 minutes using rapid tests. You can also request home-based testing through community health workers.",
        category="hiv",
        keywords=["hiv", "testing", "test", "aids", "confidential", "free"],
        translations={
            "bem": "Ukupima HIV kwapatikana pa cibinda conse. Ni apa maali, kabili ukupima kwakusisa.",
            "ny": "Kuyeza HIV kumapezeka ku zipatala zonse. Ndi kwaulere komanso mwachinsinsi.",
        },
        region_specific="Zambia - 11.0% prevalence (15-49 years)",
    ),
    FAQEntry(
        question="What is the treatment for HIV in Zambia?",
        answer="Zambia uses the WHO-recommended TLD regimen: Tenofovir (T), Lamivudine (3C), and Dolutegravir (D) as a single daily tablet. ART (Antiretroviral Therapy) is free at all public health facilities. Treatment is lifelong. With proper adherence, people living with HIV can have normal, healthy lives and the virus becomes undetectable.",
        category="hiv",
        keywords=["hiv", "treatment", "art", "tld", "tenofovir", "dolutegravir", "antiretroviral"],
        translations={
            "bem": "Umuti wa HIV mu Zambia ni TLD (Tenofovir, Lamivudine, Dolutegravir). Ni uwapaali. Mule ya pa muntu onse.",
        },
    ),
    FAQEntry(
        question="Can HIV-positive mothers breastfeed?",
        answer="Yes, HIV-positive mothers on effective ART can breastfeed exclusively for the first 6 months, as per Zambian and WHO guidelines. The risk of transmission through breastfeeding is very low (<1%) when the mother has an undetectable viral load. Both mother and infant should continue ART/ prophylaxis throughout breastfeeding. Mixed feeding should be avoided.",
        category="maternal",
        keywords=["hiv", "breastfeeding", "pregnancy", "mother", "baby", "transmission"],
        translations={
            "ny": "Amayi omwe ali ndi HIV komanso akumwa mankhwala bwino amatha kuyamwitsa mwana mpaka miyezi 6.",
        },
        requires_professional=True,
    ),
    # ---- TB ----
    FAQEntry(
        question="What are the signs of TB?",
        answer="Common signs of TB include: persistent cough for more than 2 weeks, night sweats, weight loss, fever, and chest pain. If you have these symptoms, visit your nearest health facility for free testing. Zambia uses GeneXpert as the first-line test for TB. Treatment is free and lasts 6 months. TB is curable.",
        category="tb",
        keywords=["tb", "tuberculosis", "cough", "night sweats", "weight loss"],
        translations={
            "bem": "Ifyo TB ilanga: ukukosomola ukupitila mu milungu ibili, ukutunta, ukubula ubukilo, ukubaba mu cifulo.",
            "ny": "Zizindikiro za TB: chifuwa chopitilira masabata 2, thukuta usiku, kuonda, kutentha thupi.",
        },
        region_specific="Zambia - high TB/HIV co-infection rate",
    ),
    FAQEntry(
        question="How long does TB treatment take?",
        answer="Standard TB treatment takes 6 months. The first 2 months (intensive phase) use 4 drugs: Rifampicin, Isoniazid, Pyrazinamide, and Ethambutol. The remaining 4 months (continuation phase) use 2 drugs: Rifampicin and Isoniazid. For drug-resistant TB (MDR-TB), treatment can take 9-18 months. All TB treatment is free in Zambia.",
        category="tb",
        keywords=["tb", "treatment", "duration", "6 months", "rifampicin", "rhze"],
    ),
    # ---- COVID-19 ----
    FAQEntry(
        question="Is COVID-19 still a concern in Zambia?",
        answer="COVID-19 continues to circulate but is now managed as an endemic respiratory illness in Zambia. Testing, vaccination, and treatment are available at health facilities. Vulnerable groups (elderly, those with chronic conditions) should take extra precautions. Vaccination is recommended for all eligible persons.",
        category="covid-19",
        keywords=["covid", "coronavirus", "pandemic", "vaccine", "zambia"],
        translations={
            "bem": "COVID-19 taila pwa. Ukupima, ukubayisha, no kupwa cibatu kumapatikana mu fibundwa.",
        },
    ),
    FAQEntry(
        question="Where can I get COVID-19 vaccination in Zambia?",
        answer="COVID-19 vaccines are available at all public health facilities, hospitals, and selected private clinics across Zambia. Vaccination is free. Available vaccines include Johnson & Johnson, AstraZeneca, and Pfizer. Booster doses are recommended for priority groups.",
        category="covid-19",
        keywords=["covid", "vaccine", "vaccination", "johnson", "pfizer", "astrazeneca"],
    ),
    # ---- NHIMA / Health Insurance ----
    FAQEntry(
        question="What is NHIMA and how do I register?",
        answer="NHIMA (National Health Insurance Management Authority) is Zambia's national health insurance scheme. All formally employed Zambians contribute 1% of their salary, with employers matching 1%. This covers the employee and up to 5 dependents. You can register at any NHIMA office or online at www.nhima.co.zm. Benefits include outpatient, inpatient, maternity, and emergency care at accredited facilities.",
        category="nhima",
        keywords=["nhima", "insurance", "health insurance", "registration", "contribution", "benefits"],
        translations={
            "bem": "NHIMA ni inshuwalansi ya bubilo mu Zambia. Abombele mu ma office balipila 1% ya malipilo yabo.",
        },
        region_specific="Zambia National Health Insurance Scheme",
    ),
    FAQEntry(
        question="What services does NHIMA cover?",
        answer="NHIMA covers: outpatient consultations at accredited facilities, inpatient care (up to specified limits), maternity services (antenatal, delivery, postnatal), emergency care, essential medicines on the NHIMA formulary, laboratory tests, radiology services, and dental care. There are annual benefit limits. Some services may require co-payment or pre-authorization.",
        category="nhima",
        keywords=["nhima", "coverage", "benefits", "services", "outpatient", "maternity"],
    ),
    # ---- Clinic Navigation ----
    FAQEntry(
        question="What should I bring to a clinic visit in Zambia?",
        answer="Bring: your NUPI (National Unique Patient Identifier) card or number, national ID or passport, NHIMA card if registered, previous medical records and medication history, any lab results or referral letters, and a small amount of money for any non-covered services. Arrive early, as queues can be long at public facilities.",
        category="clinic_navigation",
        keywords=["clinic", "visit", "bring", "nupi", "nhima", "records", "appointment"],
        translations={
            "bem": "Leta: NUPI kadi, ID, makalata ya cibunda, na NHIMA kadi nga mwalembesha.",
            "ny": "Bweretsani: NUPI kadi, ID, NHIMA kadi, zolemba zakale za chipatala.",
        },
    ),
    FAQEntry(
        question="How do I get a NUPI (National Unique Patient Identifier)?",
        answer="NUPI is a unique patient identifier used across all health facilities in Zambia. You get it when you first visit any health facility. The health facility will register you in the SmartCare system and issue a NUPI card. This number follows you throughout your healthcare journey in Zambia. Always carry your NUPI card.",
        category="clinic_navigation",
        keywords=["nupi", "smartcare", "identifier", "registration", "card"],
        translations={
            "bem": "NUPI mulekwata ilyo mwaya pa cibunda. Cibunda cimulembela mu SmartCare.",
        },
    ),
    # ---- Child Health ----
    FAQEntry(
        question="What vaccines does my child need in Zambia?",
        answer="Zambia follows the WHO Expanded Programme on Immunization (EPI). The schedule is: BCG and OPV at birth; OPV, PCV13, and Rotavirus at 6 weeks; OPV, PCV13, Rotavirus, and IPV at 10 weeks; OPV, PCV13, IPV at 14 weeks; Measles-Rubella at 9 months and 18 months. All vaccines are free at public health facilities.",
        category="child_health",
        keywords=["vaccines", "immunization", "child", "baby", "epi", "bcg", "polio"],
        translations={
            "bem": "Ububayo bwa bana mu Zambia: BCG na pa mweo at birth; OPV pa milungu 6.",
            "ny": "Katundu wa katemera ku Zambia: BCG ndi OPO pobadwa; OPV pa milungu 6.",
        },
        region_specific="Zambia EPI Schedule",
    ),
    FAQEntry(
        question="What is severe acute malnutrition and how is it treated?",
        answer="Severe acute malnutrition (SAM) is diagnosed when a child has MUAC <11.5cm, or severe wasting, or nutritional edema. In Zambia, SAM is treated at health facilities using Ready-to-Use Therapeutic Food (RUTF), like Plumpy'Nut. Treatment is free. Community-based management (CMAM) is available at most clinics. Early detection saves lives.",
        category="child_health",
        keywords=["malnutrition", "sam", "muac", "plumpynut", "rutf", "child feeding"],
        region_specific="Zambia - high stunting rate (35%)",
    ),
    # ---- Maternal Health ----
    FAQEntry(
        question="How many antenatal visits should I have during pregnancy?",
        answer="Zambia follows the WHO 8-contact model for antenatal care. You should visit the clinic: before 12 weeks, at 20 weeks, at 26 weeks, at 30 weeks, at 34 weeks, at 36 weeks, at 38 weeks, and at 40 weeks. All antenatal services are free at public facilities. You will receive iron, folate, malaria prophylaxis (IPTp), and HIV testing.",
        category="maternal",
        keywords=["antenatal", "pregnancy", "visits", "anc", "prenatal", "contacts"],
        translations={
            "bem": "Pa maka, mwelela ku cibunda pa miku 8. Yonse ni apa maali.",
            "ny": "Muyenera kupita ku chipatala nthawi 8 pamimba. Ndi kwaulere konse.",
        },
    ),
    FAQEntry(
        question="Where should I deliver my baby in Zambia?",
        answer="All pregnant women in Zambia are encouraged to deliver at a health facility with a skilled birth attendant. Deliveries are free at all public facilities. Choose a facility close to you with 24-hour service. If you live far, consider using a maternity waiting home near the facility in your last weeks. Emergency transport can be arranged through the clinic.",
        category="maternal",
        keywords=["delivery", "birth", "baby", "maternity", "skilled birth attendant"],
        translations={
            "bem": "Mufyale ku cibunda. Yonse ni apa maali. Bakafwako abakwafwilisha.",
        },
    ),
    # ---- Common Medications ----
    FAQEntry(
        question="What is the recommended malaria prophylaxis for pregnant women?",
        answer="Pregnant women in Zambia should receive Intermittent Preventive Treatment in pregnancy (IPTp) with Sulfadoxine-Pyrimethamine (SP/Fansidar) at each antenatal visit after 16 weeks, at least one month apart. IPTp is free at all public health facilities. It significantly reduces maternal and infant mortality.",
        category="medications",
        keywords=["iptp", "malaria", "pregnancy", "fansidar", "sulfadoxine", "prophylaxis"],
        region_specific="Zambia - malaria-endemic country",
    ),
    FAQEntry(
        question="Are medications free in Zambia?",
        answer="Essential medicines are free at all public health facilities in Zambia. This includes medicines for malaria, HIV, TB, and common illnesses. Some medications may require purchase from private pharmacies if not available at the facility. NHIMA members get additional coverage for medicines on the NHIMA formulary. The Zambia Medicines and Medical Supplies Agency (ZAMMSA) supplies public facilities.",
        category="medications",
        keywords=["medications", "free", "zammed", "zammsa", "pharmacy", "medicine"],
        translations={
            "bem": "Imisho iyapwa mu ma cibunda ya paali. Imisho ya malaria, HIV, TB yonse ni apa maali.",
        },
    ),
    # ---- Emergency ----
    FAQEntry(
        question="What is the emergency number in Zambia?",
        answer="The national emergency number in Zambia is 112 for all emergencies (police, fire, medical). For medical emergencies specifically, you can call the District Health Emergency Operations Centre or go directly to the nearest health facility. Ambulance services are available but limited, especially in rural areas. Contact your nearest clinic for emergency transport arrangements.",
        category="emergency",
        keywords=["emergency", "ambulance", "112", "hospital", "urgent"],
        translations={
            "bem": "Inamba ya fluungo mu Zambia: 112. Itanafyo fye.",
            "ny": "Nambala yadzidzithu ku Zambia: 112.",
        },
        region_specific="Zambia - limited ambulance coverage in rural areas",
    ),
]


class FAQDatabase:
    def __init__(self):
        self._faqs = FAQ_DATABASE

    def search(
        self,
        query: str,
        language: str = "en",
        category: Optional[str] = None,
        max_results: int = 5,
    ) -> List[FAQEntry]:
        query_lower = query.lower()
        results: List[tuple[float, FAQEntry]] = []

        for faq in self._faqs:
            score = 0.0
            if any(kw in query_lower for kw in faq.keywords):
                score += 3.0
            if any(word in faq.question.lower() for word in query_lower.split()):
                score += 2.0
            if any(word in faq.answer.lower() for word in query_lower.split()):
                score += 1.0
            if category and faq.category == category:
                score += 1.0
            if faq.translations.get(language):
                score += 0.5

            if score > 0:
                results.append((score, faq))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:max_results]]

    def get_by_category(self, category: str) -> List[FAQEntry]:
        return [faq for faq in self._faqs if faq.category == category]

    def get_categories(self) -> List[str]:
        return list(dict.fromkeys(faq.category for faq in self._faqs))

    def get_languages(self) -> List[str]:
        return list(dict.fromkeys(faq.language for faq in self._faqs))

    def get_translation(self, faq: FAQEntry, language: str) -> str:
        return faq.translations.get(language, faq.answer)
