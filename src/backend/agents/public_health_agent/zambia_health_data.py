from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProvinceHealthData:
    name: str
    population: int
    districts: List[str]
    hospitals: int
    clinics: int
    health_posts: int
    malaria_incidence_per_1000: float
    hiv_prevalence_pct: float
    tb_incidence_per_100k: float
    immunization_coverage_pct: float
    maternal_mortality_ratio: int
    under5_mortality_per_1000: int
    stunting_pct: float
    wasting_pct: float
    art_coverage_pct: float
    tb_treatment_success_pct: float


PROVINCE_DATA: Dict[str, ProvinceHealthData] = {
    "Central": ProvinceHealthData(
        name="Central",
        population=1_923_889,
        districts=["Chibombo", "Kabwe", "Kapiri Mposhi", "Mkushi", "Mumbwa", "Ngabwe", "Serenje", "Shibuyunji"],
        hospitals=25,
        clinics=205,
        health_posts=142,
        malaria_incidence_per_1000=320.5,
        hiv_prevalence_pct=12.4,
        tb_incidence_per_100k=204.0,
        immunization_coverage_pct=76.0,
        maternal_mortality_ratio=213,
        under5_mortality_per_1000=68,
        stunting_pct=38.0,
        wasting_pct=5.2,
        art_coverage_pct=85.0,
        tb_treatment_success_pct=87.0,
    ),
    "Copperbelt": ProvinceHealthData(
        name="Copperbelt",
        population=2_757_539,
        districts=["Chililabombwe", "Chingola", "Kalulushi", "Kitwe", "Luanshya", "Lufwanyama", "Masaiti", "Mpongwe", "Mufulira", "Ndola"],
        hospitals=38,
        clinics=264,
        health_posts=167,
        malaria_incidence_per_1000=280.3,
        hiv_prevalence_pct=15.2,
        tb_incidence_per_100k=278.0,
        immunization_coverage_pct=79.0,
        maternal_mortality_ratio=195,
        under5_mortality_per_1000=62,
        stunting_pct=34.0,
        wasting_pct=4.8,
        art_coverage_pct=89.0,
        tb_treatment_success_pct=84.0,
    ),
    "Eastern": ProvinceHealthData(
        name="Eastern",
        population=2_454_788,
        districts=["Chadiza", "Chasefu", "Chipangali", "Chipata", "Kasenengwa", "Katete", "Lumezi", "Lundazi", "Lusangazi", "Mambwe", "Nyimba", "Petauke", "Sinda", "Vubwi"],
        hospitals=22,
        clinics=231,
        health_posts=178,
        malaria_incidence_per_1000=412.8,
        hiv_prevalence_pct=9.8,
        tb_incidence_per_100k=186.0,
        immunization_coverage_pct=72.0,
        maternal_mortality_ratio=235,
        under5_mortality_per_1000=75,
        stunting_pct=42.0,
        wasting_pct=6.1,
        art_coverage_pct=81.0,
        tb_treatment_success_pct=86.0,
    ),
    "Luapula": ProvinceHealthData(
        name="Luapula",
        population=1_519_378,
        districts=["Chembe", "Chiengi", "Chifunabuli", "Chipili", "Kawambwa", "Lunga", "Mansa", "Milenge", "Mwansabombwe", "Mwense", "Nchelenge", "Samfya"],
        hospitals=16,
        clinics=154,
        health_posts=135,
        malaria_incidence_per_1000=450.2,
        hiv_prevalence_pct=8.5,
        tb_incidence_per_100k=215.0,
        immunization_coverage_pct=68.0,
        maternal_mortality_ratio=252,
        under5_mortality_per_1000=82,
        stunting_pct=45.0,
        wasting_pct=7.0,
        art_coverage_pct=77.0,
        tb_treatment_success_pct=83.0,
    ),
    "Lusaka": ProvinceHealthData(
        name="Lusaka",
        population=3_079_964,
        districts=["Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa"],
        hospitals=42,
        clinics=256,
        health_posts=98,
        malaria_incidence_per_1000=198.5,
        hiv_prevalence_pct=17.5,
        tb_incidence_per_100k=385.0,
        immunization_coverage_pct=82.0,
        maternal_mortality_ratio=178,
        under5_mortality_per_1000=55,
        stunting_pct=28.0,
        wasting_pct=4.2,
        art_coverage_pct=92.0,
        tb_treatment_success_pct=85.0,
    ),
    "Muchinga": ProvinceHealthData(
        name="Muchinga",
        population=1_049_927,
        districts=["Chama", "Chinsali", "Isoka", "Kanchibiya", "Lavushimanda", "Mpika", "Nakonde", "Nsama", "Shiwang'andu"],
        hospitals=14,
        clinics=138,
        health_posts=112,
        malaria_incidence_per_1000=365.4,
        hiv_prevalence_pct=7.2,
        tb_incidence_per_100k=168.0,
        immunization_coverage_pct=71.0,
        maternal_mortality_ratio=228,
        under5_mortality_per_1000=78,
        stunting_pct=41.0,
        wasting_pct=5.8,
        art_coverage_pct=79.0,
        tb_treatment_success_pct=86.0,
    ),
    "Northern": ProvinceHealthData(
        name="Northern",
        population=1_524_946,
        districts=["Kasama", "Lunte", "Luwingu", "Mbala", "Mporokoso", "Mpulungu", "Mungwi", "Nsobe", "Senga"],
        hospitals=18,
        clinics=167,
        health_posts=124,
        malaria_incidence_per_1000=395.6,
        hiv_prevalence_pct=7.8,
        tb_incidence_per_100k=182.0,
        immunization_coverage_pct=73.0,
        maternal_mortality_ratio=241,
        under5_mortality_per_1000=80,
        stunting_pct=43.0,
        wasting_pct=6.5,
        art_coverage_pct=80.0,
        tb_treatment_success_pct=84.0,
    ),
    "North-Western": ProvinceHealthData(
        name="North-Western",
        population=1_118_817,
        districts=["Chavuma", "Ikelenge", "Kabompo", "Kasempa", "Manyinga", "Mufumbwe", "Mushindamo", "Mwenezi", "Solwezi", "Zambezi"],
        hospitals=15,
        clinics=129,
        health_posts=108,
        malaria_incidence_per_1000=385.2,
        hiv_prevalence_pct=6.5,
        tb_incidence_per_100k=195.0,
        immunization_coverage_pct=69.0,
        maternal_mortality_ratio=245,
        under5_mortality_per_1000=79,
        stunting_pct=40.0,
        wasting_pct=5.5,
        art_coverage_pct=76.0,
        tb_treatment_success_pct=82.0,
    ),
    "Southern": ProvinceHealthData(
        name="Southern",
        population=2_381_728,
        districts=["Chikankata", "Choma", "Gwembe", "Kalomo", "Kazungula", "Livingstone", "Mazabuka", "Monze", "Namwala", "Pemba", "Siavonga", "Sinazongwe", "Zimba"],
        hospitals=28,
        clinics=218,
        health_posts=156,
        malaria_incidence_per_1000=265.8,
        hiv_prevalence_pct=13.8,
        tb_incidence_per_100k=235.0,
        immunization_coverage_pct=77.0,
        maternal_mortality_ratio=208,
        under5_mortality_per_1000=65,
        stunting_pct=35.0,
        wasting_pct=4.9,
        art_coverage_pct=86.0,
        tb_treatment_success_pct=87.0,
    ),
    "Western": ProvinceHealthData(
        name="Western",
        population=1_472_517,
        districts=["Kalabo", "Kaoma", "Limulunga", "Luampa", "Lukulu", "Mitete", "Mongu", "Mulobezi", "Mwandi", "Nalolo", "Nkeyema", "Senanga", "Sesheke", "Shangombo", "Sikongo", "Sioma"],
        hospitals=18,
        clinics=158,
        health_posts=145,
        malaria_incidence_per_1000=435.0,
        hiv_prevalence_pct=9.2,
        tb_incidence_per_100k=198.0,
        immunization_coverage_pct=67.0,
        maternal_mortality_ratio=258,
        under5_mortality_per_1000=84,
        stunting_pct=44.0,
        wasting_pct=6.8,
        art_coverage_pct=78.0,
        tb_treatment_success_pct=83.0,
    ),
}


@dataclass
class DiseaseOutbreakData:
    disease: str
    province: str
    district: str
    suspected_cases: int
    confirmed_cases: int
    deaths: int
    reporting_date: str
    status: str
    notes: str = ""


class ZambiaHealthData:
    def __init__(self):
        self._province_data = PROVINCE_DATA

    def get_province(self, name: str) -> Optional[ProvinceHealthData]:
        return self._province_data.get(name)

    def get_all_provinces(self) -> List[ProvinceHealthData]:
        return list(self._province_data.values())

    def get_districts_in_province(self, province_name: str) -> List[str]:
        province = self.get_province(province_name)
        return province.districts if province else []

    def get_national_summary(self) -> Dict[str, Any]:
        total_pop = sum(p.population for p in self._province_data.values())
        avg_malaria = sum(p.malaria_incidence_per_1000 * p.population for p in self._province_data.values()) / total_pop if total_pop else 0
        avg_hiv = sum(p.hiv_prevalence_pct * p.population for p in self._province_data.values()) / total_pop if total_pop else 0
        avg_tb = sum(p.tb_incidence_per_100k * p.population for p in self._province_data.values()) / total_pop if total_pop else 0
        avg_immunization = sum(p.immunization_coverage_pct * p.population for p in self._province_data.values()) / total_pop if total_pop else 0
        total_hospitals = sum(p.hospitals for p in self._province_data.values())
        total_clinics = sum(p.clinics for p in self._province_data.values())

        return {
            "total_population": total_pop,
            "total_hospitals": total_hospitals,
            "total_clinics": total_clinics,
            "avg_malaria_incidence_per_1000": round(avg_malaria, 1),
            "avg_hiv_prevalence_pct": round(avg_hiv, 1),
            "avg_tb_incidence_per_100k": round(avg_tb, 1),
            "avg_immunization_coverage_pct": round(avg_immunization, 1),
            "provinces": len(self._province_data),
            "total_districts": sum(len(p.districts) for p in self._province_data.values()),
        }

    def get_malaria_hotspots(self, threshold_per_1000: float = 350.0) -> List[ProvinceHealthData]:
        return [p for p in self._province_data.values() if p.malaria_incidence_per_1000 >= threshold_per_1000]

    def get_low_immunization_provinces(self, threshold_pct: float = 75.0) -> List[ProvinceHealthData]:
        return [p for p in self._province_data.values() if p.immunization_coverage_pct < threshold_pct]

    def get_high_hiv_provinces(self, threshold_pct: float = 10.0) -> List[ProvinceHealthData]:
        return [p for p in self._province_data.values() if p.hiv_prevalence_pct >= threshold_pct]

    def facility_distribution(self, province_name: Optional[str] = None) -> Dict[str, Any]:
        if province_name:
            p = self.get_province(province_name)
            if not p:
                return {}
            return {
                "province": p.name,
                "hospitals": p.hospitals,
                "clinics": p.clinics,
                "health_posts": p.health_posts,
                "total": p.hospitals + p.clinics + p.health_posts,
                "ratio_per_10000": round((p.hospitals + p.clinics + p.health_posts) / (p.population / 10000), 2),
            }

        total = {"hospitals": 0, "clinics": 0, "health_posts": 0}
        for p in self._province_data.values():
            total["hospitals"] += p.hospitals
            total["clinics"] += p.clinics
            total["health_posts"] += p.health_posts
        total["total"] = total["hospitals"] + total["clinics"] + total["health_posts"]
        return total

    def immunization_gap_analysis(self) -> List[Dict[str, Any]]:
        return [
            {
                "province": p.name,
                "coverage_pct": p.immunization_coverage_pct,
                "gap_to_target_pct": max(0, 95.0 - p.immunization_coverage_pct),
                "population": p.population,
                "unvaccinated_children_estimated": int(p.population * 0.036 * (1 - p.immunization_coverage_pct / 100)),
            }
            for p in sorted(self._province_data.values(), key=lambda x: x.immunization_coverage_pct)
        ]

    def disease_burden_summary(self) -> Dict[str, Any]:
        return {
            "malaria": {
                "highest_province": max(self._province_data.values(), key=lambda p: p.malaria_incidence_per_1000).name,
                "lowest_province": min(self._province_data.values(), key=lambda p: p.malaria_incidence_per_1000).name,
                "national_average_per_1000": round(
                    sum(p.malaria_incidence_per_1000 * p.population for p in self._province_data.values())
                    / sum(p.population for p in self._province_data.values()),
                    1,
                ),
            },
            "hiv": {
                "highest_province": max(self._province_data.values(), key=lambda p: p.hiv_prevalence_pct).name,
                "lowest_province": min(self._province_data.values(), key=lambda p: p.hiv_prevalence_pct).name,
                "national_average_pct": round(
                    sum(p.hiv_prevalence_pct * p.population for p in self._province_data.values())
                    / sum(p.population for p in self._province_data.values()),
                    1,
                ),
            },
            "tb": {
                "highest_province": max(self._province_data.values(), key=lambda p: p.tb_incidence_per_100k).name,
                "lowest_province": min(self._province_data.values(), key=lambda p: p.tb_incidence_per_100k).name,
                "national_average_per_100k": round(
                    sum(p.tb_incidence_per_100k * p.population for p in self._province_data.values())
                    / sum(p.population for p in self._province_data.values()),
                    1,
                ),
            },
        }
