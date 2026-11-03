"""Seed knowledge base with WHO/Zambia treatment guidelines, disease info, protocols.

Revision ID: 003
Revises: 002
Create Date: 2026-06-17
"""

from typing import Optional, Sequence

from alembic import op
from sqlalchemy import text

revision: str = "003"
down_revision: Optional[str] = "002"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    _seed_who_guidelines()
    _seed_zambia_treatment_guidelines()
    _seed_essential_medicines_list()
    _seed_immunization_schedule()
    _seed_maternal_health_protocols()
    _seed_common_diseases_multilingual()
    _seed_public_health_guidance()


def downgrade() -> None:
    op.execute("DELETE FROM knowledge_base")


def _seed_who_guidelines() -> None:
    entries = [
        # Malaria
        ("malaria", "uncomplicated", "en",
         "WHO Guidelines: Uncomplicated Malaria Treatment",
         """WHO recommends artemisinin-based combination therapy (ACT) for uncomplicated P. falciparum malaria.
First-line: Artemether + Lumefantrine (AL) for 3 days.
Alternative: Artesunate + Amodiaquine (AS+AQ), Dihydroartemisinin + Piperaquine.
Treatment should be based on confirmed parasitological diagnosis where possible.
In pregnancy: 1st trimester - Quinine + Clindamycin for 7 days. 2nd/3rd trimester - ACT as per national policy.
Children: Weight-based dosing. AL: 5-14kg: 1 tab (20/120mg) twice daily for 3 days; 15-24kg: 2 tabs; 25-34kg: 3 tabs; >34kg: 4 tabs."""),

        ("malaria", "severe", "en",
         "WHO Guidelines: Severe Malaria Management",
         """Severe malaria requires parenteral treatment.
First-line: Artesunate 2.4mg/kg IV or IM (2.4mg/kg at 0, 12, 24 hours for IV; IM: 2.4mg/kg at 0, 12, 24 hours then daily).
Alternative (if artesunate unavailable): Artemether 3.2mg/kg IM loading dose, then 1.6mg/kg daily.
OR Quinine 20mg/kg loading dose (max 1.4g), then 10mg/kg 8-hourly.
Switch to oral ACT when patient can tolerate oral medication.
Pre-referral: Artesunate 100mg suppository (rectal) or Artemether IM if available.
Monitor for hypoglycaemia, pulmonary oedema, acute kidney injury."""),

        ("malaria", "prevention", "en",
         "WHO Guidelines: Malaria Prevention (Zambia)",
         """WHO recommends the following prevention measures:
1. Insecticide-treated nets (ITNs) - universal coverage in malaria-endemic areas
2. Intermittent Preventive Treatment in pregnancy (IPTp) - Sulfadoxine-Pyrimethamine at each ANC visit from 16 weeks (at least 3 doses)
3. Seasonal Malaria Chemoprevention (SMC) - for children under 5 in Sahel sub-region
4. Indoor Residual Spraying (IRS) - in epidemic-prone areas
Zambia MoH recommends ITNs for all households, IPTp-SP for all pregnant women, and IRS in targeted high-burden districts."""),

        # HIV
        ("hiv", "treatment", "en",
         "WHO Guidelines: HIV Antiretroviral Therapy (ART)",
         """WHO recommends ART for all people with HIV regardless of CD4 count.
First-line: TLD - Tenofovir (TDF) 300mg + Lamivudine (3TC) 300mg + Dolutegravir (DTG) 50mg once daily.
Alternative: TLE - Tenofovir + Lamivudine + Efavirenz 600mg.
Second-line: AZT + 3TC + boosted PI (Lopinavir/Ritonavir or Atazanavir/Ritonavir).
Third-line: New drug classes (integrase inhibitors, PIs, NNRTIs) based on resistance testing.
Test and Treat: Initiate ART as soon as possible after diagnosis (same-day initiation preferred).
Prevention: PrEP with TDF/FTC for HIV-negative individuals at substantial risk."""),

        ("hiv", "pediatric", "en",
         "WHO Guidelines: Pediatric HIV Treatment",
         """Children < 10 years:
First-line: ABC + 3TC + DTG (or LPV/r if < 4 weeks or < 3kg).
Weight-based dosing for DTG: 3-6kg: 5mg dispersible once daily; 6-10kg: 10mg; 10-14kg: 15mg; 14-20kg: 20mg; >20kg: 30mg.
Infant diagnosis: HIV PCR at birth/6 weeks, rapid test at 18 months.
All HIV-exposed infants receive NVP prophylaxis for 6-12 weeks (or longer if breast-feeding)."""),

        ("hiv", "prevention", "en",
         "WHO Guidelines: Prevention of Mother-to-Child Transmission (PMTCT)",
         """Option B+ approach: All pregnant/breastfeeding women with HIV start lifelong ART (TLD).
Infant prophylaxis: Nevirapine (NVP) daily from birth to 6-12 weeks (or until cessation of breastfeeding).
Exclusive breastfeeding for 6 months, then complementary feeding with continued breastfeeding to 12 months.
Early infant diagnosis: HIV PCR at 6 weeks, serology at 18 months.
Follow WHO guidelines for infant feeding in the context of HIV: avoid mixed feeding."""),

        # TB
        ("tb", "treatment", "en",
         "WHO Guidelines: Tuberculosis Treatment",
         """Drug-susceptible TB: 6-month regimen (2HRZE/4HR).
Intensive phase (2 months): Rifampicin + Isoniazid + Pyrazinamide + Ethambutol daily.
Continuation phase (4 months): Rifampicin + Isoniazid daily.
New shorter regimen: 4-month regimen (2HPZM/2HPM) for DS-TB.
MDR-TB: All-oral longer regimen (18-20 months) with fluoroquinolone, bedaquiline, linezolid.
All-oral shorter regimen (9-12 months): Bedaquiline, Levofloxacin/Moxifloxacin, Ethionamide, ETH, PZA, INH high-dose, Clofazimine.
Directly Observed Therapy (DOT) recommended for all patients."""),

        ("tb", "prevention", "en",
         "WHO Guidelines: TB Preventive Treatment (TPT)",
         """TPT recommended for:
1. All HIV-positive individuals (test for TB first)
2. Household contacts of confirmed TB cases (especially children < 5 years)
3. People on immunosuppressive therapy
Regimens: 6H (6 months Isoniazid); 3HP (3 months INH + Rifapentine once weekly); 3HR (3 months INH + Rifampicin daily); 9H (9 months Isoniazid)
Zambia uses 3HP (weekly) for TPT roll-out."""),

        # Cholera
        ("cholera", "treatment", "en",
         "WHO Guidelines: Cholera Case Management",
         """Cholera is a medical emergency requiring immediate rehydration.
Plan A (No dehydration): ORS at home. Continue feeding.
Plan B (Some dehydration): 75ml/kg ORS over 4 hours (or Ringer's Lactate if unable to drink).
Plan C (Severe dehydration): IV fluids (Ringer's Lactate) rapidly. Adults: 100ml/kg in 3 hours. Children: 30ml/kg in 30 min, then 70ml/kg in 2.5 hours.
Antibiotics for severe cases: Doxycycline 300mg single dose (adults); Azithromycin 20mg/kg single dose (children, pregnant).
Zinc supplementation: 20mg/day for children (reduces duration and severity).
Cholera beds (cholera cots) essential for monitoring stool output.
Refer to ORP (Outbreak Response Plan) guidelines."""),

        # COVID-19
        ("covid19", "treatment", "en",
         "WHO Guidelines: COVID-19 Clinical Management",
         """Mild disease: Symptomatic management, home isolation if appropriate (5 days).
Moderate (pneumonia): Hospital monitoring, oxygen if needed, dexamethasone 6mg daily for 10 days.
Severe (severe pneumonia): Oxygen therapy, dexamethasone, therapeutic anticoagulation, consider tocilizumab or baricitinib.
Critical (ARDS): ICU care, mechanical ventilation, prone positioning, dexamethasone, consider baricitinib/tocilizumab.
Antiviral therapy: Paxlovid (nirmatrelvir/ritonavir) for high-risk patients within 5 days of symptom onset.
COVID-19 vaccination recommended per national schedule."""),

        # WHO guidelines in English
        ("respiratory_infection", "treatment", "en",
         "WHO Guidelines: Acute Respiratory Infection Management",
         """WHO Integrated Management of Childhood Illness (IMCI) approach:
Classify severity: no pneumonia, pneumonia, severe pneumonia.
Pneumonia (fast breathing): Amoxicillin 50mg/kg/day for 5 days (or dispersible tablets 250mg).
Severe pneumonia (chest indrawing, stridor): Refer to hospital. Benzylpenicillin / Ampicillin + Gentamicin.
Non-severe: Home care with antibiotics and follow-up in 2 days.
Oxygen therapy: SpO2 < 90% is indication for oxygen (target > 90%)."""),

        ("diarrhoea", "treatment", "en",
         "WHO Guidelines: Diarrhoea Management (IMCI)",
         """WHO IMCI approach for diarrhoea:
Classify: Some dehydration or severe dehydration using IMCI chart.
Plan A (no dehydration): ORS + Zinc 20mg for 14 days + continued feeding.
Plan B (some dehydration): 75ml/kg ORS over 4 hours with monitoring.
Plan C (severe dehydration): IV fluids per plan.
Zinc reduces stool output and duration - ALWAYS prescribe with ORS.
Routine antibiotics only for: dysentery (blood in stool), suspected cholera, or confirmed shigella.
No anti-diarrhoeal drugs for children under 5."""),

        ("malnutrition", "treatment", "en",
         "WHO Guidelines: Severe Acute Malnutrition Management",
         """WHO 10-step protocol for SAM management:
Phase 1 (Stabilization): 1) Treat hypoglycaemia, 2) Treat hypothermia, 3) Treat dehydration, 4) Correct electrolyte imbalance, 5) Treat infection.
Phase 2 (Rehabilitation): 6) Initiate refeeding (F75 then F100), 7) Catch-up growth, 8) Provide sensory stimulation and emotional support.
Phase 3 (Follow-up): 9) Prepare for discharge, 10) Long-term follow-up.
Therapeutic milk: F75 (75 kcal/100ml) for stabilization; F100 (100 kcal/100ml) for rehabilitation.
RUTF (Plumpy'Nut): For community-based management of uncomplicated SAM.
MUAC: < 11.5cm for SAM, 11.5-12.5cm for MAM in children 6-59 months."""),
    ]
    for cat, subcat, lang, title, content in entries:
        op.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'WHO Guidelines')
        """))


def _seed_zambia_treatment_guidelines() -> None:
    entries = [
        ("zambia_treatment", "malaria", "en",
         "Zambia Standard Treatment Guidelines: Malaria",
         """Zambia's National Malaria Elimination Programme (NMEP) guidelines:
Uncomplicated malaria (confirmed RDT+): Artemether-Lumefantrine (AL) for 3 days.
First trimester pregnancy: Quinine + Clindamycin for 7 days.
Severe malaria: IV Artesunate 2.4mg/kg at 0, 12, 24h.
Pre-referral: Rectal Artesunate (100mg suppository).
IPTp: SP (3 doses) at ANC visits from 16 weeks.
Malaria is endemic in all 10 provinces of Zambia, with peak transmission in rainy season (November-April)."""),

        ("zambia_treatment", "hiv", "en",
         "Zambia National HIV/AIDS Treatment Guidelines",
         """Zambia MoH follows WHO 2021 guidelines with 'Test and Treat' approach:
First-line (adults): TLD (TDF 300mg + 3TC 300mg + DTG 50mg) once daily.
If contraindicated to TDF: AZT/ABC + 3TC + DTG.
First-line (children): ABC + 3TC + DTG (weight-based dosing).
Second-line: AZT + 3TC + LPV/r (or ATV/r).
HIV testing: Provider-initiated testing and counselling (PITC) in all health facilities.
Zambia's HIV prevalence: approximately 11% (15-49 years). VL monitoring at 6 months and 12 months, then annually."""),

        ("zambia_treatment", "tb", "en",
         "Zambia National TB Programme (NTP) Guidelines",
         """Drug-susceptible TB: 2HRZE/4HR (6 months).
MDR/RR-TB: All-oral shorter regimen (9-12 months) with Bedaquiline, Levofloxacin/Moxifloxacin, Clofazimine, ETH, PZA, INH high-dose, E.
TB/HIV co-management: All TB patients tested for HIV; all HIV+ TB patients on ART (TLD) regardless of CD4.
TPT: 3HP (3 months weekly INH + Rifapentine) for all PLHIV and household contacts.
Zambia has high TB burden with approximately 60,000 cases annually."""),

        ("zambia_treatment", "cholera", "en",
         "Zambia Cholera Management Protocol (MoH)",
         """Zambia experiences seasonal cholera outbreaks (October-May). Management:
Rapid assessment: dehydration status (none, some, severe).
Plan C (severe): IV Ringer's Lactate, reassess every 15-30min.
Antibiotic: Azithromycin 1g single dose (adults) or Doxycycline 300mg single dose.
ORS: Start as soon as patient can drink.
Zinc: 20mg for 10-14 days for children under 5.
Disinfection: Chlorine solution for contaminated surfaces; proper disposal of stools.
Oral Cholera Vaccine (OCV): pre-emptive campaigns in high-risk areas (shantytowns, peri-urban).
Notify District Health Office immediately. Case-area targeted intervention (CATI) within 48 hours."""),

        ("zambia_treatment", "maternal", "en",
         "Zambia Maternal Health Guidelines",
         """Zambia MoH focuses on reducing maternal mortality (current ~213/100,000):
Focused Antenatal Care (FANC): 8+ contacts recommended.
IPTp-SP: starting at 16 weeks, monthly until delivery.
Syphilis screening: RDT at first contact; treat positive with Benzathine penicillin 2.4MU IM once weekly x 3.
HIV testing: at first contact, repeat at 32 weeks and during labour.
PMTCT: Option B+ - lifelong ART for all HIV+ pregnant women.
TB screening: at each ANC contact.
Skilled birth attendance: All deliveries in health facilities.
Postnatal care: within 24h of birth, day 3, day 7-14, 6 weeks."""),
    ]
    for cat, subcat, lang, title, content in entries:
        op.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'Zambia Ministry of Health')
        """))


def _seed_essential_medicines_list() -> None:
    op.execute(text("""
        INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
        VALUES ('essential_medicines', 'zambia', 'en',
            'Zambia Essential Medicines List (EML)',
            'The Zambia Essential Medicines List (EML) is based on the WHO Model List of Essential Medicines adapted for the Zambian disease burden. Key categories: Antimalarials (AL, Artesunate, Quinine, SP); Antiretrovirals (TLD, AZT+3TC, LPV/r, DTG, ABC); TB medicines (RHZE, RH, Bedaquiline, Delamanid, Linezolid); Antibiotics (Amoxicillin, Ceftriaxone, Azithromycin, Doxycycline, Metronidazole, Ciprofloxacin, Gentamicin); Maternal health (Oxytocin, Misoprostol, MgSO4, Ergometrine); Chronic disease (Metformin, Glibenclamide, Amlodipine, Enalapril, Salbutamol, Atorvastatin); Vaccines per EPI schedule; ORS and Zinc for diarrhoea; Vitamin A supplementation.',
            'Zambia Ministry of Health / WHO')
    """))


def _seed_immunization_schedule() -> None:
    op.execute(text("""
        INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
        VALUES ('immunization', 'epi_schedule', 'en',
            'Zambia Expanded Programme on Immunization (EPI) Schedule 2024',
            'Zambia EPI Schedule: At birth: BCG, OPV0. 6 weeks: PENTA1, PCV1, ROTA1, OPV1. 10 weeks: PENTA2, PCV2, ROTA2, OPV2. 14 weeks: PENTA3, PCV3, IPV, OPV3. 9 months: Measles-Rubella (MR) 1, Yellow Fever. 18 months: MR2, booster. 24 months: Vitamin A. Pregnant women: TT/Td at first contact, then 4-week intervals. HPV: 2 doses at 9-14 years (6-month interval). All vaccines are free of charge at all government health facilities. Vitamin A supplementation: 6 months (100,000 IU), 12-59 months (200,000 IU) every 6 months.',
            'Zambia Ministry of Health - EPI Program')
    """))


def _seed_maternal_health_protocols() -> None:
    entries = [
        ("maternal_health", "anc", "en",
         "Focused Antenatal Care (FANC) Protocol - 8+ Contacts",
         """Contact 1 (<12 weeks): Confirm pregnancy, HIV test, syphilis test, Hb, blood group, urinalysis, BP, weight, IPTp-SP, ITN, Td1, deworming, ferrous sulfate + folic acid, calcium if pre-eclampsia risk.
Contact 2 (20 weeks): BP, weight, IPTp-SP, fetal heart rate, fundal height, syphilis repeat.
Contact 3 (26 weeks): BP, weight, glucose screening, Hb, IPTp-SP.
Contact 4 (30 weeks): BP, weight, fundal height, fetal presentation, IPTp-SP.
Contact 5 (34 weeks): BP, weight, fetal presentation, Td2.
Contact 6 (36 weeks): BP, weight, fetal presentation, birth planning, danger signs.
Contact 7 (38 weeks): BP, weight, fetal presentation.
Contact 8 (40 weeks): BP, weight, fetal presentation, post-term plan.
Danger signs: vaginal bleeding, severe headache, blurred vision, reduced fetal movements, fever, abdominal pain, dysuria, breathlessness."""),

        ("maternal_health", "labour", "en",
         "Zambia Labour and Delivery Management Protocol",
         """Partograph for all women in active labour.
Active phase: begins at 4cm cervical dilation.
First stage: monitor contractions, FH, cervical dilation 4-hourly.
Second stage: full dilation to delivery (up to 2 hours nullipara, 1 hour multipara).
Active management of third stage of labour (AMTSL): Oxytocin 10IU IM within 1 minute of delivery, controlled cord traction, uterine massage.
Newborn care: immediate drying, skin-to-skin, delayed cord clamping (1-3 min), Vitamin K 1mg IM, Tetracycline eye ointment, BCG and OPV0, birth weight, exclusive breastfeeding.
Complications: PPH (Oxytocin IV, Misoprostol 800mcg SL, Tranexamic acid), Eclampsia (MgSO4 4g IV loading + 5g IM maintenance), Sepsis (broad-spectrum antibiotics)."""),
    ]
    for cat, subcat, lang, title, content in entries:
        op.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'Zambia Ministry of Health / WHO')
        """))


def _seed_common_diseases_multilingual() -> None:
    entries = [
        # English
        ("disease_info", "malaria", "en",
         "Malaria (Information for Patients)",
         """Malaria is a serious disease spread by mosquitoes. Symptoms: fever, headache, chills, vomiting, muscle pain. If you have a fever, go to the clinic immediately for a malaria test. Treatment is free at government clinics. Prevent malaria by: sleeping under an insect-treated bed net every night, clearing bushes around your home, and pregnant women taking SP medicine at the clinic."""),
        ("disease_info", "hiv", "en",
         "HIV (Information for Patients)",
         """HIV is a virus that weakens the immune system. It is spread through unprotected sex, contaminated needles, and from mother to child during pregnancy/breastfeeding. HIV testing is free and confidential at all health facilities. If you test positive, you will be started on free treatment (ART) the same day. With proper treatment, people with HIV live long, healthy lives. Treatment also prevents passing HIV to others (U=U). Protect yourself: use condoms, know your status, take PrEP if at high risk."""),
        ("disease_info", "tb", "en",
         "Tuberculosis (TB) - Information for Patients",
         """TB is a bacterial infection that usually affects the lungs. Symptoms: cough for more than 2 weeks, night sweats, weight loss, fever, chest pain. If you have a persistent cough, go to the nearest clinic for a free sputum test. TB is curable with 6 months of free medicine. Take your TB medicine every day without missing doses - directly observed by a health worker. Cover your mouth when coughing. TB treatment is free."""),
        ("disease_info", "cholera", "en",
         "Cholera - Information for Patients",
         """Cholera is a diarrhoeal disease caused by contaminated water or food. It causes severe watery diarrhoea and vomiting leading to rapid dehydration. Cholera can kill within hours if untreated. If you have watery diarrhoea, go to the nearest health facility immediately. Treatment: ORS (oral rehydration salts) and zinc for children. Cholera is preventable: drink boiled or chlorinated water, wash hands with soap after toilet and before eating, use latrines, cook food thoroughly."""),
        ("disease_info", "covid19", "en",
         "COVID-19 - Information for Patients",
         """COVID-19 is a respiratory illness caused by coronavirus. Symptoms: fever, cough, difficulty breathing, loss of taste/smell, body aches. Most people recover at home. Seek medical help if you have difficulty breathing, chest pain, confusion, or high fever. Prevention: get vaccinated, wear a mask in crowded places, wash hands frequently, keep distance. COVID-19 vaccines are free and available at all health facilities."""),

        # Bemba translations
        ("disease_info", "malaria", "bem",
         "Malaria (Ubukulu bwakuuma)",
         """Malaria ni bulwale bukulu bwishinka na mibalaba. Ubushibo mu: umupili, umutwe, ukutinta, ukwafya, ububabwa mu minofu. Ngamwipwilwa ukwaba, yeni mu cipataala pakupima malali. Imiti ya Malaria tailipwa mumi cipataala. Mupe malaria: mwepapo motwe kumutubaasha pakucesha, mupe ubulelo ubupokelela."""),
        ("disease_info", "hiv", "bem",
         "HIV (Ukukankala Ukukulu)",
         """HIV ni akanyele kankanya amasambililo yabumi. Kapwaishisha mu kufwila pa bulanda (ukufwila pa bulanda), naumana pamo na kubukwata busha. Ukwepesha HIV kabili kabili mumafwamfwa mecipatala cenu. Mwinsumina ukwepesha bwanta."""),
        ("disease_info", "diarrhoea", "bem",
         "Ukupwaula (Diarrhoea)",
         """Ukupwaula ni bulwale bwakumana na meeya ayaba ni ma bacteria mu munda. Mufwa ubushiku mwena meeya? Yeni mu cipatala. Ukufwaya: ORS na Zinc. Ukupwaula kuti baumfwa ngomupwaula meeya yakutetela."""),
        ("disease_info", "tb", "bem",
         "TB (Icifuba)",
         """TB ni bulwale bwakomana na bakashashi. Ubushifo bukulu ni: ukukosola kwapita milungu ibili, ukukonka ubushiku, ukubuntula. Ukukosola kwapita milungu ibili? Yeni mu cipatala. Ukupima TB cawala (tailipwa). Imiti ya TB tailipwa ni yabwanta. Mwenwe imiti yonse iyuuba."""),

        # Nyanja translations
        ("disease_info", "malaria", "nya",
         "Malaria (Matenda a Malungo)",
         """Malungo ndi matenda oopsa amene amafala kudzera pa udzudzule. Zizindikiro: kutentha thupi, mutu ululu, kugwedeza, kusanza, kupweteka kwa minofu. Ngati muli ndi malungo, pitani kuchipatala msanga kuti mukazunzike. Mankhwala a malungo ndi aulere. Tetezani: gondolani pansi pa chitseko cha udzudzule."""),
        ("disease_info", "hiv", "nya",
         "HIV (Kachilombo ka HIV)",
         """HIV ndi kachilombo kamene kamafooketsa chitetezo cha mthupi. Kufala kudzera pa kugonana, majekeseni, kapena kuchokera kwa mayi kwa mwana. Kuzunzika kwa HIV ndi kwaulere. Mukapezeka ndi HIV, mupeza mankhwala aulere tsiku lomwelo. Chitetezani: gwiritsani makondomu, mudziwe mkhalidwe wanu."""),
        ("disease_info", "cholera", "nya",
         "Kolera (Matenda a Kholera)",
         """Kholera ndi matenda otulutsa m'mimba omwe amafala kudzera m'madzi oipa. Zizindikiro: kutulutsa m'mimba kwamadzi, kusanza kwambiri. Izi zikhoza kupha msanga. Mukayamba kutulutsa m'mimba, pitani kuchipatala msanga. Tetezani: kuwiritsa madzi, kutsuka manja ndi sopo."""),
        ("disease_info", "tb", "nya",
         "TB (Chifuwa chachikulu)",
         """Chifuwa chachikulu ndi matenda a bakiteriya omwe amakhudza mapapo. Zizindikiro: chifuwa chapyolela masabata awiri, kutuluka thukuta usiku, kuonda thupi. Chifuwa chapyolela masabata awiri? Pitani kuchipatala. Kupima ndi mankhwala ndi kwaulere. Mankhwala a TB ndi aulere."""),
    ]
    for cat, subcat, lang, title, content in entries:
        op.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'Zambia Ministry of Health')
        """))


def _seed_public_health_guidance() -> None:
    entries = [
        ("public_health", "water_sanitation", "en",
         "Water, Sanitation and Hygiene (WASH) Guidelines for Health Facilities",
         """Minimum WASH standards for health facilities in Zambia:
Drinking water: improved source within 500m, 5 litres per outpatient per day, 40-60 litres per inpatient per day.
Sanitation: one toilet per 20 outpatients, one per 10 inpatients. Separate toilets for men/women.
Hand hygiene: handwashing stations with soap and water at all points of care, toilets, and food preparation areas.
Waste management: colour-coded bins (black - general; yellow - infectious; red - sharps; green - pharmaceutical).
Placenta pit for obstetric waste. Incinerator for infectious waste. Autoclave for reusable instruments.
Chlorine solution preparation: 0.5% for surface disinfection, 0.05% for hand hygiene."""),

        ("public_health", "outbreak", "en",
         "Zambia Integrated Disease Surveillance and Response (IDSR)",
         """Zambia uses IDSR framework for outbreak detection and response. Priority diseases requiring immediate notification (within 24 hours): Cholera, Yellow Fever, Measles, Polio, Viral Haemorrhagic Fevers (Ebola, Marburg), Meningococcal Meningitis, Rabies, Anthrax, Maternal death, Perinatal death.
Reporting: Health facilities report to District Health Office -> Provincial Health Office -> MoH.
Weekly zero-reporting: all facilities report even with zero cases.
Community-based surveillance: community health workers report unusual health events.
Alert thresholds: Cholera - 1 suspected case; Measles - 1 suspected case; AFP - 1 case in child <15 years."""),

        ("public_health", "nutrition", "en",
         "Zambia Nutrition Guidelines",
         """Infant and Young Child Feeding (IYCF):
Exclusive breastfeeding for first 6 months. Continued breastfeeding up to 2 years or more.
Complementary feeding from 6 months: appropriate, adequate, safe, frequent.
Vitamin A supplementation: 6-11 months (100,000 IU), 12-59 months (200,000 IU) every 6 months.
Iron supplementation: children 6-24 months (12.5mg iron/50mcg folic acid daily for 3 months).
Management of acute malnutrition: MUAC screening at all under-5 clinics. SAM program with RUTF. MAM program with CSB++. 
Growth monitoring: monthly for children under 1, quarterly for 1-2 years."""),

        ("public_health", "ncd", "en",
         "Zambia NCD Management Guidelines (Hypertension, Diabetes)",
         """Screening: BP and blood glucose/urine dipstick at all outpatient contacts for adults >40 years, earlier if symptomatic.
Hypertension management: lifestyle modification (diet, exercise, salt reduction, smoking cessation, alcohol reduction).
First-line antihypertensive: Amlodipine 5mg daily. Second-line: add Enalapril 5-10mg daily. Third-line: add Hydrochlorothiazide 12.5-25mg daily.
Target BP: <140/90 mmHg (<130/80 if diabetic or CKD).
Diabetes management: lifestyle modification + Metformin 500mg twice daily (increase up to 2g daily). Add Glibenclamide 5mg if poorly controlled.
Target HbA1c: <7% (53 mmol/mol). Monitoring: HbA1c every 6 months, annual eye exam, annual foot exam, annual renal function.
Diabetes complications screening: retinopathy, neuropathy, nephropathy, cardiovascular disease."""),
    ]
    for cat, subcat, lang, title, content in entries:
        op.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'Zambia Ministry of Health / WHO')
        """))


if __name__ == "__main__":
    upgrade()
