"""Seed Zambia geographic, health facility, and clinical reference data.

Revision ID: 002
Revises: 001
Create Date: 2026-06-17
"""

from typing import Optional, Sequence

from alembic import op
from sqlalchemy import text

revision: str = "002"
down_revision: Optional[str] = "001"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    _seed_provinces()
    _seed_districts()
    _seed_facility_types()
    _seed_health_facilities()
    _seed_medicines()
    _seed_lab_tests()
    _seed_vaccines()
    _seed_roles_and_permissions()
    _seed_common_diagnoses()
    _seed_sample_hospitals()


def downgrade() -> None:
    op.execute("DELETE FROM user_roles")
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")
    op.execute("DELETE FROM immunizations")
    op.execute("DELETE FROM vaccine_stock")
    op.execute("DELETE FROM prescriptions")
    op.execute("DELETE FROM lab_results")
    op.execute("DELETE FROM lab_orders")
    op.execute("DELETE FROM lab_test_catalog")
    op.execute("DELETE FROM clinical_notes")
    op.execute("DELETE FROM vitals")
    op.execute("DELETE FROM visits")
    op.execute("DELETE FROM patients")
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM inventory_items")
    op.execute("DELETE FROM health_facilities")
    op.execute("DELETE FROM districts")
    op.execute("DELETE FROM provinces")
    op.execute("DELETE FROM ai_model_cache")
    op.execute("DELETE FROM knowledge_base")


# ── Provinces ──────────────────────────────────────────────────────────────

def _seed_provinces() -> None:
    op.execute(text("""
        INSERT INTO provinces (id, code, name, capital, population, area_sq_km) VALUES
        (1, 'LK', 'Lusaka', 'Lusaka', 3782737, 21896),
        (2, 'CB', 'Copperbelt', 'Ndola', 2893241, 31328),
        (3, 'CT', 'Central', 'Kabwe', 1807575, 94394),
        (4, 'ST', 'Southern', 'Choma', 2107721, 85283),
        (5, 'ET', 'Eastern', 'Chipata', 2265153, 69106),
        (6, 'NR', 'Northern', 'Kasama', 1545658, 77868),
        (7, 'WT', 'Western', 'Mongu', 1203600, 126386),
        (8, 'LP', 'Luapula', 'Mansa', 1280766, 50567),
        (9, 'MG', 'Muchinga', 'Chinsali', 985651, 87606),
        (10, 'NW', 'North-Western', 'Solwezi', 1203283, 125826)
    """))


def _seed_districts() -> None:
    districts = [
        # Lusaka (province_id=1)
        ("Lusaka", 1, "LK001"), ("Chilanga", 1, "LK002"), ("Kafue", 1, "LK003"),
        ("Luangwa", 1, "LK004"), ("Chongwe", 1, "LK005"), ("Rufunsa", 1, "LK006"),
        ("Shibuyunji", 1, "LK007"),
        # Copperbelt (province_id=2)
        ("Ndola", 2, "CB001"), ("Kitwe", 2, "CB002"), ("Chingola", 2, "CB003"),
        ("Mufulira", 2, "CB004"), ("Luanshya", 2, "CB005"), ("Kalulushi", 2, "CB006"),
        ("Chililabombwe", 2, "CB007"), ("Mpongwe", 2, "CB008"), ("Lufwanyama", 2, "CB009"),
        ("Masaiti", 2, "CB010"),
        # Central (province_id=3)
        ("Kabwe", 3, "CT001"), ("Mkushi", 3, "CT002"), ("Serenje", 3, "CT003"),
        ("Mumbwa", 3, "CT004"), ("Chibombo", 3, "CT005"), ("Chisamba", 3, "CT006"),
        ("Kapiri Mposhi", 3, "CT007"), ("Itezhi-Tezhi", 3, "CT008"), ("Ngabwe", 3, "CT009"),
        # Southern (province_id=4)
        ("Choma", 4, "ST001"), ("Livingstone", 4, "ST002"), ("Mazabuka", 4, "ST003"),
        ("Monze", 4, "ST004"), ("Kalomo", 4, "ST005"), ("Namwala", 4, "ST006"),
        ("Gwembe", 4, "ST007"), ("Sinazongwe", 4, "ST008"), ("Kazungula", 4, "ST009"),
        ("Pemba", 4, "ST010"), ("Zimba", 4, "ST011"),
        # Eastern (province_id=5)
        ("Chipata", 5, "ET001"), ("Petauke", 5, "ET002"), ("Katete", 5, "ET003"),
        ("Lundazi", 5, "ET004"), ("Chadiza", 5, "ET005"), ("Nyimba", 5, "ET006"),
        ("Sinda", 5, "ET007"), ("Vubwi", 5, "ET008"), ("Mambwe", 5, "ET009"),
        ("Kasenengwa", 5, "ET010"),
        # Northern (province_id=6)
        ("Kasama", 6, "NR001"), ("Mbala", 6, "NR002"), ("Mpulungu", 6, "NR003"),
        ("Luwingu", 6, "NR004"), ("Mungwi", 6, "NR005"), ("Mporokoso", 6, "NR006"),
        ("Nsama", 6, "NR007"), ("Senga Hill", 6, "NR008"),
        # Western (province_id=7)
        ("Mongu", 7, "WT001"), ("Senanga", 7, "WT002"), ("Sesheke", 7, "WT003"),
        ("Kaoma", 7, "WT004"), ("Kalabo", 7, "WT005"), ("Lukulu", 7, "WT006"),
        ("Shangombo", 7, "WT007"), ("Limulunga", 7, "WT008"), ("Nkeyema", 7, "WT009"),
        ("Sioma", 7, "WT010"), ("Mitete", 7, "WT011"),
        # Luapula (province_id=8)
        ("Mansa", 8, "LP001"), ("Chembe", 8, "LP002"), ("Mwansabombwe", 8, "LP003"),
        ("Samfya", 8, "LP004"), ("Kawambwa", 8, "LP005"), ("Nchelenge", 8, "LP006"),
        ("Milenge", 8, "LP007"), ("Mwense", 8, "LP008"), ("Chifunabuli", 8, "LP009"),
        ("Lunga", 8, "LP010"),
        # Muchinga (province_id=9)
        ("Chinsali", 9, "MG001"), ("Isoka", 9, "MG002"), ("Nakonde", 9, "MG003"),
        ("Mpika", 9, "MG004"), ("Chama", 9, "MG005"), ("Shiwang''andu", 9, "MG006"),
        ("Kanchibiya", 9, "MG007"), ("Lavushimanda", 9, "MG008"),
        # North-Western (province_id=10)
        ("Solwezi", 10, "NW001"), ("Kasempa", 10, "NW002"), ("Mufumbwe", 10, "NW003"),
        ("Kabompo", 10, "NW004"), ("Zambezi", 10, "NW005"), ("Mwinilunga", 10, "NW006"),
        ("Chavuma", 10, "NW007"), ("Ikelenge", 10, "NW008"), ("Manyinga", 10, "NW009"),
        ("Kalumbila", 10, "NW010"), ("Musondwisho", 10, "NW011"), ("Mushindamo", 10, "NW012"),
    ]
    for name, province_id, code in districts:
        op.execute(text(f"""
            INSERT INTO districts (code, name, province_id)
            VALUES ('{code}', '{name}', {province_id})
        """))


# ── Facility Types ──────────────────────────────────────────────────────────

def _seed_facility_types() -> None:
    pass  # Handled by ENUM type and health facilities table


# ── Health Facilities ───────────────────────────────────────────────────────

def _seed_health_facilities() -> None:
    facilities = [
        # Lusaka facilities
        ("UH001", "University Teaching Hospital", "tertiary_hospital", "LK001", 1, -15.3875, 28.3228, "Nationalist Road, Lusaka", "260211234567", 3500, True, True, True, True, True, True, 1655),
        ("LK001", "Lusaka District Health Office", "urban_health_centre", "LK001", 1, -15.4067, 28.2846, "Freedom Way, Lusaka", "260211123456", 500, True, True, True, True, True, False, 50),
        ("MTH001", "Matero Main Clinic", "urban_clinic", "LK001", 1, -15.3333, 28.2333, "Matero, Lusaka", "260211654321", 200, True, True, True, False, True, False, 30),
        ("CHE001", "Chelstone Clinic", "urban_clinic", "LK001", 1, -15.3667, 28.3667, "Chelstone, Lusaka", "260211987654", 150, True, True, True, True, True, False, 20),
        ("KNW001", "Kanyama Clinic", "urban_health_centre", "LK001", 1, -15.4167, 28.2667, "Kanyama, Lusaka", "260211345678", 180, True, True, False, False, True, False, 25),
        ("CHG001", "Chilenje Clinic", "urban_clinic", "LK001", 1, -15.3850, 28.3000, "Chilenje, Lusaka", "260211456789", 120, True, True, True, True, True, False, 15),
        ("KFE001", "Kafue District Hospital", "district_hospital", "LK003", 1, -15.7667, 28.1833, "Kafue Town", "260211567890", 120, True, True, True, False, True, False, 120),
        ("LGW001", "Luangwa District Hospital", "district_hospital", "LK004", 1, -15.6167, 30.4167, "Luangwa Town", "260211678901", 80, True, False, False, True, False, False, 60),
        # Copperbelt facilities
        ("NDH001", "Ndola Teaching Hospital", "tertiary_hospital", "CB001", 2, -12.9667, 28.6333, "Ndola", "260212123456", 2500, True, True, True, True, True, True, 850),
        ("KTW001", "Kitwe Teaching Hospital", "tertiary_hospital", "CB002", 2, -12.8167, 28.2000, "Kitwe", "260212234567", 2200, True, True, True, True, True, True, 700),
        ("CHL001", "Chingola General Hospital", "general_hospital", "CB003", 2, -12.5333, 27.8500, "Chingola", "260212345678", 800, True, True, True, True, True, True, 300),
        ("MFL001", "Mufulira District Hospital", "district_hospital", "CB004", 2, -12.5500, 28.2500, "Mufulira", "260212456789", 600, True, True, True, True, True, False, 250),
        ("LNS001", "Luanshya District Hospital", "district_hospital", "CB005", 2, -13.1333, 28.4000, "Luanshya", "260212567890", 500, True, True, True, True, True, False, 200),
        ("KLL001", "Kalulushi General Hospital", "general_hospital", "CB006", 2, -12.8333, 28.0833, "Kalulushi", "260212678901", 350, True, True, True, False, True, False, 150),
    ]
    for code, name, ftype, dcode, pid, lat, lng, addr, phone, pop, elec, water, internet, solar, coldchain, oxygen, beds in facilities:
        op.execute(text(f"""
            INSERT INTO health_facilities (
                code, name, facility_type, district_id, province_id,
                latitude, longitude, address, phone, catchment_population,
                has_electricity, has_water, has_internet, has_solar_power,
                has_cold_chain, has_oxygen_plant, num_beds
            ) VALUES (
                '{code}', '{name}', '{ftype}',
                (SELECT id FROM districts WHERE code = '{dcode}'),
                {pid}, {lat}, {lng}, '{addr}', '{phone}', {pop},
                {str(elec).lower()}, {str(water).lower()}, {str(internet).lower()},
                {str(solar).lower()}, {str(coldchain).lower()}, {str(oxygen).lower()}, {beds}
            )
        """))


# ── Essential Medicines ──────────────────────────────────────────────────────

def _seed_medicines() -> None:
    medicines = [
        ("ART001", "Artemether + Lumefantrine 20/120mg", "Antimalarial", "Tablet"),
        ("ART002", "Artesunate 60mg injection", "Antimalarial", "Injection"),
        ("ART003", "Artesunate 50mg suppository", "Antimalarial", "Suppository"),
        ("ART004", "Artemether 80mg injection", "Antimalarial", "Injection"),
        ("ART005", "Chloroquine 150mg base tablet", "Antimalarial", "Tablet"),
        ("ART006", "Primaquine 7.5mg tablet", "Antimalarial", "Tablet"),
        ("ART007", "Quinine 300mg tablet", "Antimalarial", "Tablet"),
        ("ART008", "Quinine 300mg/ml injection", "Antimalarial", "Injection"),
        ("ART009", "Sulfadoxine + Pyrimethamine 500/25mg", "Antimalarial", "Tablet"),
        ("ART010", "Doxycycline 100mg capsule", "Antimalarial", "Capsule"),
        ("HIV001", "Tenofovir + Lamivudine + Dolutegravir (TLD)", "Antiretroviral", "Tablet"),
        ("HIV002", "Tenofovir + Lamivudine (TL)", "Antiretroviral", "Tablet"),
        ("HIV003", "Zidovudine + Lamivudine (AZT+3TC)", "Antiretroviral", "Tablet"),
        ("HIV004", "Efavirenz 600mg tablet", "Antiretroviral", "Tablet"),
        ("HIV005", "Nevirapine 200mg tablet", "Antiretroviral", "Tablet"),
        ("HIV006", "Lopinavir + Ritonavir 100/25mg", "Antiretroviral", "Tablet"),
        ("HIV007", "Abacavir 300mg tablet", "Antiretroviral", "Tablet"),
        ("HIV008", "Dolutegravir 50mg tablet", "Antiretroviral", "Tablet"),
        ("HIV009", "Zidovudine syrup 10mg/ml", "Antiretroviral", "Syrup"),
        ("HIV010", "Nevirapine syrup 10mg/ml", "Antiretroviral", "Syrup"),
        ("TB001", "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol (RHZE)", "Antituberculosis", "Tablet"),
        ("TB002", "Rifampicin + Isoniazid (RH)", "Antituberculosis", "Tablet"),
        ("TB003", "Isoniazid 300mg tablet", "Antituberculosis", "Tablet"),
        ("TB004", "Rifampicin 150mg capsule", "Antituberculosis", "Capsule"),
        ("TB005", "Ethambutol 400mg tablet", "Antituberculosis", "Tablet"),
        ("TB006", "Pyrazinamide 400mg tablet", "Antituberculosis", "Tablet"),
        ("TB007", "Streptomycin 1g injection", "Antituberculosis", "Injection"),
        ("TB008", "Bedaquiline 100mg tablet", "Antituberculosis", "Tablet"),
        ("TB009", "Delamanid 50mg tablet", "Antituberculosis", "Tablet"),
        ("TB010", "Linezolid 600mg tablet", "Antituberculosis", "Tablet"),
        ("ABX001", "Amoxicillin 250mg capsule", "Antibiotic", "Capsule"),
        ("ABX002", "Amoxicillin 500mg capsule", "Antibiotic", "Capsule"),
        ("ABX003", "Amoxicillin suspension 125mg/5ml", "Antibiotic", "Suspension"),
        ("ABX004", "Amoxicillin + Clavulanic acid 625mg", "Antibiotic", "Tablet"),
        ("ABX005", "Ceftriaxone 1g injection", "Antibiotic", "Injection"),
        ("ABX006", "Ciprofloxacin 500mg tablet", "Antibiotic", "Tablet"),
        ("ABX007", "Azithromycin 500mg tablet", "Antibiotic", "Tablet"),
        ("ABX008", "Metronidazole 400mg tablet", "Antibiotic", "Tablet"),
        ("ABX009", "Gentamicin 80mg injection", "Antibiotic", "Injection"),
        ("ABX010", "Penicillin V 250mg tablet", "Antibiotic", "Tablet"),
        ("ABX011", "Cloxacillin 500mg capsule", "Antibiotic", "Capsule"),
        ("ABX012", "Doxycycline 100mg capsule", "Antibiotic", "Capsule"),
        ("ABX013", "Erythromycin 250mg tablet", "Antibiotic", "Tablet"),
        ("ABX014", "Nitrofurantoin 100mg capsule", "Antibiotic", "Capsule"),
        ("ABX015", "Sulfamethoxazole + Trimethoprim 400/80mg", "Antibiotic", "Tablet"),
        ("ABX016", "Chloramphenicol 250mg capsule", "Antibiotic", "Capsule"),
        ("ABX017", "Chloramphenicol eye drops 0.5%", "Antibiotic", "Eye Drops"),
        ("ABX018", "Tetracycline eye ointment 1%", "Antibiotic", "Eye Ointment"),
        ("CVD001", "Amlodipine 5mg tablet", "Cardiovascular", "Tablet"),
        ("CVD002", "Amlodipine 10mg tablet", "Cardiovascular", "Tablet"),
        ("CVD003", "Enalapril 5mg tablet", "Cardiovascular", "Tablet"),
        ("CVD004", "Enalapril 10mg tablet", "Cardiovascular", "Tablet"),
        ("CVD005", "Hydrochlorothiazide 25mg tablet", "Cardiovascular", "Tablet"),
        ("CVD006", "Furosemide 40mg tablet", "Cardiovascular", "Tablet"),
        ("CVD007", "Digoxin 0.25mg tablet", "Cardiovascular", "Tablet"),
        ("CVD008", "Aspirin 75mg tablet", "Cardiovascular", "Tablet"),
        ("CVD009", "Aspirin 300mg tablet", "Cardiovascular", "Tablet"),
        ("CVD010", "Atorvastatin 10mg tablet", "Cardiovascular", "Tablet"),
        ("CVD011", "Metoprolol 50mg tablet", "Cardiovascular", "Tablet"),
        ("CVD012", "Nifedipine 10mg capsule", "Cardiovascular", "Capsule"),
        ("RES001", "Salbutamol inhaler 100mcg", "Respiratory", "Inhaler"),
        ("RES002", "Salbutamol 4mg tablet", "Respiratory", "Tablet"),
        ("RES003", "Beclometasone inhaler 100mcg", "Respiratory", "Inhaler"),
        ("RES004", "Prednisolone 5mg tablet", "Respiratory", "Tablet"),
        ("RES005", "Aminophylline 100mg tablet", "Respiratory", "Tablet"),
        ("RES006", "Dexamethasone 4mg injection", "Respiratory", "Injection"),
        ("GIS001", "Omeprazole 20mg capsule", "Gastrointestinal", "Capsule"),
        ("GIS002", "Ranitidine 150mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS003", "Oral Rehydration Salts (ORS)", "Gastrointestinal", "Powder"),
        ("GIS004", "Zinc sulfate 20mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS005", "Albendazole 400mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS006", "Mebendazole 500mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS007", "Mebendazole suspension 100mg/5ml", "Gastrointestinal", "Suspension"),
        ("GIS008", "Hyoscine butylbromide 10mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS009", "Loperamide 2mg capsule", "Gastrointestinal", "Capsule"),
        ("GIS010", "Bisacodyl 5mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS011", "Metoclopramide 10mg tablet", "Gastrointestinal", "Tablet"),
        ("GIS012", "Vitamin A 200,000 IU capsule", "Gastrointestinal", "Capsule"),
        ("CNS001", "Paracetamol 500mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS002", "Paracetamol syrup 120mg/5ml", "CNS/Analgesic", "Syrup"),
        ("CNS003", "Ibuprofen 400mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS004", "Diclofenac 50mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS005", "Morphine 10mg injection", "CNS/Analgesic", "Injection"),
        ("CNS006", "Pethidine 50mg injection", "CNS/Analgesic", "Injection"),
        ("CNS007", "Diazepam 5mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS008", "Diazepam 10mg injection", "CNS/Analgesic", "Injection"),
        ("CNS009", "Phenobarbital 30mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS010", "Carbamazepine 200mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS011", "Sodium valproate 200mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS012", "Amitriptyline 25mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS013", "Fluoxetine 20mg capsule", "CNS/Analgesic", "Capsule"),
        ("CNS014", "Haloperidol 5mg tablet", "CNS/Analgesic", "Tablet"),
        ("CNS015", "Chlorpromazine 100mg tablet", "CNS/Analgesic", "Tablet"),
        ("END001", "Metformin 500mg tablet", "Endocrine", "Tablet"),
        ("END002", "Metformin 850mg tablet", "Endocrine", "Tablet"),
        ("END003", "Glibenclamide 5mg tablet", "Endocrine", "Tablet"),
        ("END004", "Insulin NPH 100IU/ml", "Endocrine", "Injection"),
        ("END005", "Insulin Regular 100IU/ml", "Endocrine", "Injection"),
        ("END006", "Levothyroxine 50mcg tablet", "Endocrine", "Tablet"),
        ("OBS001", "Oxytocin 10IU injection", "Obstetric", "Injection"),
        ("OBS002", "Misoprostol 200mcg tablet", "Obstetric", "Tablet"),
        ("OBS003", "Magnesium sulfate 50% injection", "Obstetric", "Injection"),
        ("OBS004", "Ergometrine 0.5mg injection", "Obstetric", "Injection"),
        ("OBS005", "Ferrous sulfate + Folic acid tablet", "Obstetric", "Tablet"),
        ("OBS006", "Folic acid 5mg tablet", "Obstetric", "Tablet"),
        ("OBS007", "Calcium carbonate 500mg tablet", "Obstetric", "Tablet"),
        ("OBS008", "Mebendazole 500mg (pregnancy)", "Obstetric", "Tablet"),
        ("FLU001", "Ringers Lactate 500ml", "Fluid/Electrolyte", "Infusion"),
        ("FLU002", "Normal Saline 500ml", "Fluid/Electrolyte", "Infusion"),
        ("FLU003", "Dextrose 5% 500ml", "Fluid/Electrolyte", "Infusion"),
        ("FLU004", "Dextrose 50% 50ml injection", "Fluid/Electrolyte", "Injection"),
        ("FLU005", "Potassium chloride 15% 10ml", "Fluid/Electrolyte", "Injection"),
        ("VIT001", "Multivitamin tablet", "Vitamin/Nutrition", "Tablet"),
        ("VIT002", "Vitamin B complex tablet", "Vitamin/Nutrition", "Tablet"),
        ("VIT003", "Vitamin C 100mg tablet", "Vitamin/Nutrition", "Tablet"),
        ("VIT004", "Vitamin D 400IU capsule", "Vitamin/Nutrition", "Capsule"),
    ]
    for code, name, category, unit in medicines:
        op.execute(text(f"""
            INSERT INTO inventory_items (item_code, item_name, category, facility_id,
                current_stock, minimum_stock, reorder_point, unit_of_measure, is_active)
            VALUES ('{code}', '{name.replace("'", "''")}', '{category}',
                (SELECT id FROM health_facilities LIMIT 1),
                0, 100, 200, '{unit}', true)
        """))


# ── Lab Tests ────────────────────────────────────────────────────────────────

def _seed_lab_tests() -> None:
    tests = [
        ("MAL001", "Malaria Rapid Diagnostic Test", "Parasitology", "Blood", "RDT", 15, False, True),
        ("MAL002", "Malaria Blood Smear (Thick/Thin)", "Parasitology", "Blood", "Microscopy", 60, False, False),
        ("HIV001", "HIV Rapid Test (Determine)", "Serology", "Blood", "RDT", 20, False, True),
        ("HIV002", "HIV Confirmatory Test (Uni-Gold)", "Serology", "Blood", "RDT", 20, False, True),
        ("HIV003", "HIV PCR (Early Infant Diagnosis)", "Molecular", "DBS", "PCR", 1440, True, False),
        ("HIV004", "HIV Viral Load", "Molecular", "Plasma", "PCR", 2880, True, False),
        ("TB001", "TB GeneXpert Ultra", "Molecular", "Sputum", "GeneXpert", 120, False, False),
        ("TB002", "TB Sputum Smear Microscopy", "Microbiology", "Sputum", "ZN Microscopy", 240, False, False),
        ("TB003", "TB Culture (LJ Medium)", "Microbiology", "Sputum", "Culture", 30240, True, False),
        ("TB004", "TB LAM Test (Urine)", "Serology", "Urine", "RDT", 25, False, True),
        ("TB005", "TB Drug Sensitivity Testing", "Molecular", "Sputum", "DST", 43200, True, False),
        ("SYG001", "Syphilis RDT", "Serology", "Blood", "RDT", 15, False, True),
        ("SYG002", "Syphilis TPHA", "Serology", "Blood", "Agglutination", 240, False, False),
        ("C19A01", "COVID-19 Rapid Antigen Test", "Serology", "Nasal", "RDT", 15, False, True),
        ("C19A02", "COVID-19 PCR", "Molecular", "Nasopharyngeal", "PCR", 1440, True, False),
        ("HEP001", "Hepatitis B Surface Antigen RDT", "Serology", "Blood", "RDT", 20, False, True),
        ("HEP002", "Hepatitis C Antibody RDT", "Serology", "Blood", "RDT", 20, False, True),
        ("CBC001", "Full Blood Count", "Haematology", "Blood", "Automated", 120, False, False),
        ("CBC002", "Haemoglobin (Hb) Measurement", "Haematology", "Blood", "HemoCue", 5, False, True),
        ("CBC003", "Blood Group and Rh Type", "Haematology", "Blood", "Slide/Tube", 30, False, False),
        ("CBC004", "Malaria Parasite Count", "Parasitology", "Blood", "Microscopy", 60, False, False),
        ("BCH001", "Blood Glucose (Random/Fasting)", "Biochemistry", "Blood", "Glucometer", 2, False, True),
        ("BCH002", "HbA1c", "Biochemistry", "Blood", "Chromatography", 1440, False, False),
        ("BCH003", "Renal Function (Urea/Creatinine)", "Biochemistry", "Blood", "Automated", 240, False, False),
        ("BCH004", "Liver Function Tests", "Biochemistry", "Blood", "Automated", 240, False, False),
        ("BCH005", "Serum Electrolytes (Na/K/Cl)", "Biochemistry", "Blood", "Automated", 240, False, False),
        ("BCH006", "Lipid Profile", "Biochemistry", "Blood", "Automated", 240, False, False),
        ("BCH007", "Uric Acid", "Biochemistry", "Blood", "Automated", 240, False, False),
        ("BCH008", "CRP (C-Reactive Protein)", "Biochemistry", "Blood", "RDT/Quantitative", 30, False, True),
        ("BCH009", "CD4 Count", "Immunology", "Blood", "Flow Cytometry", 240, False, False),
        ("URI001", "Urinalysis (Dipstick)", "Biochemistry", "Urine", "Dipstick", 10, False, True),
        ("URI002", "Urine Pregnancy Test (hCG)", "Biochemistry", "Urine", "RDT", 5, False, True),
        ("URI003", "Urine Culture and Sensitivity", "Microbiology", "Urine", "Culture", 2880, False, False),
        ("STO001", "Stool Microscopy (Ova/Cysts)", "Parasitology", "Stool", "Microscopy", 30, False, False),
        ("STO002", "Stool Culture", "Microbiology", "Stool", "Culture", 4320, False, False),
        ("STO003", "Vibrio cholerae RDT", "Microbiology", "Stool", "RDT", 15, False, True),
        ("CSF001", "CSF Analysis", "Biochemistry", "CSF", "Microscopy/Chemistry", 60, False, False),
        ("CSF002", "CSF GeneXpert (TB Meningitis)", "Molecular", "CSF", "GeneXpert", 120, False, False),
        ("CSF003", "CSF Cryptococcal Antigen", "Serology", "CSF", "RDT", 20, False, True),
        ("SRV001", "HPV DNA Test", "Molecular", "Cervical", "PCR", 4320, False, False),
        ("SRV002", "PAP Smear", "Histology", "Cervical", "Cytology", 4320, False, False),
        ("SRV003", "Syphilis RPR", "Serology", "Blood", "Flocculation", 240, False, False),
    ]
    for code, name, cat, specimen, method, tat, cold, rapid in tests:
        op.execute(text(f"""
            INSERT INTO lab_test_catalog (code, name, category, specimen_type, method,
                turnaround_time_minutes, requires_cold_chain, is_rapid_test)
            VALUES ('{code}', '{name.replace("'", "''")}', '{cat}', '{specimen}',
                '{method}', {tat}, {str(cold).lower()}, {str(rapid).lower()})
        """))


# ── Vaccines ─────────────────────────────────────────────────────────────────

def _seed_vaccines() -> None:
    vaccines = [
        ("BCG", "BCG (Tuberculosis)", 0, "Birth", 1, 0, 50),
        ("OPV0", "Oral Polio Vaccine (OPV)", 0, "Birth", 1, 0, 50),
        ("OPV1", "Oral Polio Vaccine (OPV)", 1, "6 weeks", 6, 0, 50),
        ("OPV2", "Oral Polio Vaccine (OPV)", 2, "10 weeks", 10, 0, 50),
        ("OPV3", "Oral Polio Vaccine (OPV)", 3, "14 weeks", 14, 0, 50),
        ("IPV", "Inactivated Polio Vaccine (IPV)", 1, "14 weeks", 14, 0, 50),
        ("PENTA1", "Pentavalent (DTP-HepB-Hib)", 1, "6 weeks", 6, 0, 50),
        ("PENTA2", "Pentavalent (DTP-HepB-Hib)", 2, "10 weeks", 10, 0, 50),
        ("PENTA3", "Pentavalent (DTP-HepB-Hib)", 3, "14 weeks", 14, 0, 50),
        ("PCV1", "Pneumococcal Conjugate (PCV)", 1, "6 weeks", 6, 0, 50),
        ("PCV2", "Pneumococcal Conjugate (PCV)", 2, "10 weeks", 10, 0, 50),
        ("PCV3", "Pneumococcal Conjugate (PCV)", 3, "14 weeks", 14, 0, 50),
        ("ROTA1", "Rotavirus Vaccine", 1, "6 weeks", 6, 0, 50),
        ("ROTA2", "Rotavirus Vaccine", 2, "10 weeks", 10, 0, 50),
        ("MEAS1", "Measles Rubella (MR)", 1, "9 months", 39, 0, 50),
        ("MEAS2", "Measles Rubella (MR)", 2, "18 months", 78, 0, 50),
        ("YF", "Yellow Fever Vaccine", 1, "9 months", 39, 0, 50),
        ("HPV1", "HPV Vaccine", 1, "9-14 years", 468, 0, 50),
        ("HPV2", "HPV Vaccine", 2, "9-14 years", 494, 0, 50),
        ("TET1", "Tetanus Toxoid (TT1)", 1, "Pregnancy 1st contact", 0, 0, 50),
        ("TET2", "Tetanus Toxoid (TT2)", 2, "Pregnancy (4 weeks after TT1)", 4, 0, 50),
        ("TET3", "Tetanus Toxoid (TT3)", 3, "Subsequent pregnancy", 0, 0, 50),
        ("TET4", "Tetanus Toxoid (TT4)", 4, "Subsequent pregnancy", 0, 0, 50),
        ("TET5", "Tetanus Toxoid (TT5)", 5, "Subsequent pregnancy", 0, 0, 50),
        ("CHOL1", "Cholera Vaccine (OCV)", 1, "6 months+", 0, 0, 50),
        ("CHOL2", "Cholera Vaccine (OCV)", 2, "2 weeks after dose 1", 2, 0, 50),
        ("MEN", "Meningococcal Vaccine", 1, "12 months", 52, 0, 50),
        ("VITA", "Vitamin A Supplementation", 1, "6 months", 26, 0, 100),
        ("VITA2", "Vitamin A Supplementation", 2, "12 months", 52, 0, 100),
        ("VITA3", "Vitamin A Supplementation", 3, "24 months", 104, 0, 100),
        ("ALB1", "Albendazole (De-worming)", 1, "12 months", 52, 0, 100),
        ("ALB2", "Albendazole (De-worming)", 2, "24 months", 104, 0, 100),
        ("COVID1", "COVID-19 Vaccine (Primary)", 1, "12 years+", 0, 0, 50),
        ("COVID2", "COVID-19 Vaccine (Booster)", 2, "4 months after primary", 16, 0, 50),
    ]
    for code, name, dose, schedule, weeks, _extra, temp in vaccines:
        op.execute(text(f"""
            INSERT INTO vaccine_stock (vaccine_code, batch_number, facility_id,
                quantity_received, quantity_dispensed, quantity_available,
                manufacturer, expiry_date, requires_cold_chain, storage_temperature_celsius)
            VALUES ('{code}', 'INIT-BATCH-001',
                (SELECT id FROM health_facilities LIMIT 1),
                0, 0, 0, 'UNICEF', '2027-12-31',
                true, {temp})
        """))


# ── Roles and Permissions ────────────────────────────────────────────────────

def _seed_roles_and_permissions() -> None:
    roles = [
        (1, "super_admin", "Full system access across all facilities", True),
        (2, "hospital_admin", "Administrative access for a hospital/facility", False),
        (3, "doctor", "Medical doctor clinical access", False),
        (4, "nurse", "Nursing staff clinical access", False),
        (5, "clinical_officer", "Clinical officer access", False),
        (6, "pharmacist", "Pharmacy access", False),
        (7, "lab_technician", "Laboratory access", False),
        (8, "community_health_worker", "Community health worker limited access", False),
        (9, "data_entry", "Data entry clerk access", False),
        (10, "moh_officer", "Ministry of Health reporting access", False),
        (11, "viewer", "Read-only access", False),
    ]
    for rid, name, desc, sys_role in roles:
        op.execute(text(f"""
            INSERT INTO roles (id, name, description, is_system_role)
            VALUES ({rid}, '{name}', '{desc}', {str(sys_role).lower()})
            ON CONFLICT (id) DO NOTHING
        """))

    permissions_data = [
        # Patient management
        ("patient:read", "View patient demographics", "patient", "read"),
        ("patient:create", "Register new patients", "patient", "create"),
        ("patient:update", "Update patient information", "patient", "update"),
        ("patient:delete", "Delete patient records", "patient", "delete"),
        ("patient:search", "Search patient records", "patient", "search"),
        # Clinical
        ("clinical:read", "View clinical notes", "clinical", "read"),
        ("clinical:write", "Write clinical notes", "clinical", "write"),
        ("clinical:sign", "Sign off clinical notes", "clinical", "sign"),
        ("clinical:diagnosis", "Add/update diagnoses", "clinical", "diagnosis"),
        # Lab
        ("lab:order", "Order laboratory tests", "lab", "order"),
        ("lab:read", "View lab results", "lab", "read"),
        ("lab:perform", "Perform lab tests and enter results", "lab", "perform"),
        ("lab:verify", "Verify lab results", "lab", "verify"),
        # Pharmacy
        ("pharmacy:prescribe", "Write prescriptions", "pharmacy", "prescribe"),
        ("pharmacy:dispense", "Dispense medications", "pharmacy", "dispense"),
        ("pharmacy:read", "View prescriptions", "pharmacy", "read"),
        ("pharmacy:manage_stock", "Manage pharmaceutical stock", "pharmacy", "manage_stock"),
        # Immunization
        ("immunization:administer", "Administer vaccines", "immunization", "administer"),
        ("immunization:read", "View immunization records", "immunization", "read"),
        ("immunization:schedule", "Schedule immunizations", "immunization", "schedule"),
        # Admin
        ("admin:users", "Manage system users", "admin", "users"),
        ("admin:roles", "Manage roles and permissions", "admin", "roles"),
        ("admin:facility", "Manage facility settings", "admin", "facility"),
        ("admin:system", "System configuration", "admin", "system"),
        ("admin:audit", "View audit logs", "admin", "audit"),
        # Reports
        ("report:analytics", "View analytics dashboards", "report", "analytics"),
        ("report:dhis2", "Generate DHIS2-compatible reports", "report", "dhis2"),
        ("report:export", "Export data", "report", "export"),
        # Sync
        ("sync:manage", "Manage sync settings", "sync", "manage"),
        ("sync:monitor", "Monitor sync status", "sync", "monitor"),
        # Community
        ("community:read", "View community health data", "community", "read"),
        ("community:write", "Record community health data", "community", "write"),
    ]
    for i, (code, name, resource, action) in enumerate(permissions_data, 1):
        op.execute(text(f"""
            INSERT INTO permissions (id, code, name, resource, action)
            VALUES ({i}, '{code}', '{name}', '{resource}', '{action}')
            ON CONFLICT (id) DO NOTHING
        """))

    role_permission_map = {
        "super_admin": list(range(1, len(permissions_data) + 1)),
        "hospital_admin": [1,2,3,5,6,8,9,10,11,13,14,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32],
        "doctor": [1,2,3,5,6,7,8,9,10,13,16,19,20],
        "clinical_officer": [1,2,3,5,6,7,8,9,10,13,16,19,20],
        "nurse": [1,2,3,5,6,8,11,16,18,19,20,32],
        "pharmacist": [1,14,15,16,17,18],
        "lab_technician": [1,10,11,12],
        "community_health_worker": [1,5,8,18,20,32],
        "data_entry": [1,2,3,5,19],
        "moh_officer": [1,5,10,13,16,19,26,27,28],
        "viewer": [1,6,10,14,16,19,26],
    }
    for role_name, perm_ids in role_permission_map.items():
        role_id = next(r[0] for r in roles if r[1] == role_name)
        for pid in perm_ids:
            op.execute(text(f"""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ({role_id}, {pid})
                ON CONFLICT DO NOTHING
            """))


# ── Common Diagnoses (ICD-10) ──────────────────────────────────────────────

def _seed_common_diagnoses() -> None:
    pass  # Data seeded via knowledge_base


# ── Sample Hospitals ─────────────────────────────────────────────────────────

def _seed_sample_hospitals() -> None:
    pass  # Already seeded facilities; this adds sample user configs
    # Create default admin user
    from uuid import uuid4
    admin_id = str(uuid4())
    op.execute(text(f"""
        INSERT INTO users (id, username, email, password_hash, first_name, last_name,
            phone, designation, is_active, is_verified, must_change_password)
        VALUES (
            '{admin_id}', 'admin', 'admin@ubuntucare.gov.zm',
            '$2b$12$LJ3m4ys3Lg3YOCwLpWYqWOeWtGHiK5RJv7vJCU0qJ8y8wKQD.k0ba',
            'System', 'Admin', '+260977000000',
            'System Administrator', true, true, false
        )
    """))
    op.execute(text(f"""
        INSERT INTO user_roles (user_id, role_id)
        VALUES ('{admin_id}', 1)
    """))

    # Create hospital admin for UTH
    admin2_id = str(uuid4())
    op.execute(text(f"""
        INSERT INTO users (id, username, email, password_hash, first_name, last_name,
            phone, designation, facility_id, is_active, is_verified)
        VALUES (
            '{admin2_id}', 'uth_admin', 'uth.admin@ubuntucare.gov.zm',
            '$2b$12$LJ3m4ys3Lg3YOCwLpWYqWOeWtGHiK5RJv7vJCU0qJ8y8wKQD.k0ba',
            'UTH', 'Admin', '+260977000001',
            'Hospital Administrator',
            (SELECT id FROM health_facilities WHERE code = 'UH001'),
            true, true
        )
    """))
    op.execute(text(f"""
        INSERT INTO user_roles (user_id, role_id)
        VALUES ('{admin2_id}', 2)
    """))

    # Create MoH user
    moh_id = str(uuid4())
    op.execute(text(f"""
        INSERT INTO users (id, username, email, password_hash, first_name, last_name,
            phone, designation, is_active, is_verified)
        VALUES (
            '{moh_id}', 'moh_officer', 'reports@moh.gov.zm',
            '$2b$12$LJ3m4ys3Lg3YOCwLpWYqWOeWtGHiK5RJv7vJCU0qJ8y8wKQD.k0ba',
            'MoH', 'Reports', '+260977000002',
            'Ministry of Health Officer', true, true
        )
    """))
    op.execute(text(f"""
        INSERT INTO user_roles (user_id, role_id)
        VALUES ('{moh_id}', 10)
    """))


if __name__ == "__main__":
    upgrade()
