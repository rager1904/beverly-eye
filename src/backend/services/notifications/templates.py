from typing import Optional


class NotificationTemplates:
    """Multi-language notification templates for Zambia."""

    LANGUAGE_CODES = {
        "en": "English",
        "bem": "Bemba",
        "nyj": "Nyanja",
        "tog": "Tonga",
        "loz": "Lozi",
    }

    @staticmethod
    def appointment_reminder(
        patient_name: str,
        datetime_str: str,
        facility: str,
        lang: str = "en",
    ) -> str:
        templates = {
            "en": f"Dear {patient_name}, this is a reminder of your appointment on {datetime_str} at {facility}. Please arrive 15 minutes early. - UbuntuCare Zambia",
            "bem": f"Mwe {patient_name}, twakumbusha pa appointment yenu pa {datetime_str} ku {facility}. Nabulangeni panono. - UbuntuCare Zambia",
            "nyj": f"Wachikondi {patient_name}, chikumbutso cha nthawi yanu pa {datetime_str} ku {facility}. Chonde fifikeni koyamba. - UbuntuCare Zambia",
            "tog": f"Mwami {patient_name}, twakukumbusya zyakukazyiwa kwenu pa {datetime_str} ku {facility}. Twalumba. - UbuntuCare Zambia",
            "loz": f"Mwa {patient_name}, ki kakuli mwa zweli kwa kukwaeli kwa lizazi la {datetime_str} kwa {facility}. Ni mwanele minu. - UbuntuCare Zambia",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def test_results_ready(patient_name: str, test_name: str, lang: str = "en") -> str:
        templates = {
            "en": f"Dear {patient_name}, your {test_name} results are ready. Please visit the facility to collect them. - UbuntuCare Zambia",
            "bem": f"Mwe {patient_name}, ifyapali fya {test_name} fyalola. Nabulangeni mu facility mupokelele. - UbuntuCare Zambia",
            "nyj": f"Wachikondi {patient_name}, zotsatira za {test_name} zafika. Chonde pitani ku chipatala kutenga. - UbuntuCare Zambia",
            "tog": f"Mwami {patient_name}, zyakuzwa kwa {test_name} zyakamana. Twalumba muzibona ku facility. - UbuntuCare Zambia",
            "loz": f"Mwa {patient_name}, lipi li {test_name} li fihile. Ni mwanele ku yo li nana kwa facility. - UbuntuCare Zambia",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def medication_reminder(
        patient_name: str,
        medication: str,
        dosage: str,
        frequency: str,
        lang: str = "en",
    ) -> str:
        templates = {
            "en": f"Dear {patient_name}, remember to take {medication} {dosage} {frequency}. - UbuntuCare Zambia",
            "bem": f"Mwe {patient_name}, ibukeni ukunwa {medication} {dosage} {frequency}. - UbuntuCare Zambia",
            "nyj": f"Wachikondi {patient_name}, kumbukirani kumwa {medication} {dosage} {frequency}. - UbuntuCare Zambia",
            "tog": f"Mwami {patient_name}, twakukumbusya kunwa {medication} {dosage} {frequency}. - UbuntuCare Zambia",
            "loz": f"Mwa {patient_name}, mu zweli ku nwa {medication} {dosage} {frequency}. - UbuntuCare Zambia",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def vaccination_reminder(
        patient_name: str,
        vaccine: str,
        date: str,
        lang: str = "en",
    ) -> str:
        templates = {
            "en": f"Dear {patient_name}, your child is due for {vaccine} on {date}. Please visit the nearest health facility. - UbuntuCare Zambia",
            "bem": f"Mwe {patient_name}, umwana wenu afwile ukupokelela {vaccine} pa {date}. Nabulangeni mu facility. - UbuntuCare Zambia",
            "nyj": f"Wachikondi {patient_name}, mwana wanu akuyenera {vaccine} pa {date}. Chonde pitani ku chipatala. - UbuntuCare Zambia",
            "tog": f"Mwami {patient_name}, mwana wanu walumba kujana {vaccine} pa {date}. Twalumba muyo ku facility. - UbuntuCare Zambia",
            "loz": f"Mwa {patient_name}, mwana wa minu u zweli ku fumaneha {vaccine} ka lizazi la {date}. Ni mwanele ku yo facility. - UbuntuCare Zambia",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def health_tip(tip_type: str, lang: str = "en") -> str:
        tips = {
            "malaria": {
                "en": "Malaria prevention: Sleep under an insecticide-treated mosquito net every night. - Ministry of Health Zambia",
                "bem": "Ukutemwa malaria: Mwishenga mumuseke uwapailwa ne mfundo ya kuipaya imikubo. - Ministry of Health Zambia",
                "nyj": "Kupewa malungo: Gonani pa neti yothana ndi udzudzu usiku uliwonse. - Ministry of Health Zambia",
                "tog": "Kuzibya malaria: Sununa mumunana wakusuntulwa muntu uyo wakusuntulilwa kujana miswa. - Ministry of Health Zambia",
                "loz": "Kusilela malaria: Mu zibise mwa neti ye itusisizwe fa miswa. - Ministry of Health Zambia",
            },
            "cholera": {
                "en": "Cholera prevention: Wash hands with soap and safe water after using the toilet and before eating. - Ministry of Health Zambia",
                "bem": "Ukutemwa cholera: Sapifweni amenso ne sopu na menshi ayasanta. - Ministry of Health Zambia",
                "nyj": "Kupewa kolera: Sambani manja ndi sopo ndi madzi abwino. - Ministry of Health Zambia",
                "tog": "Kuzibya kolera: Yakwe amaoko a sopu. - Ministry of Health Zambia",
                "loz": "Kusilela kolera: Hapanga lizoho ka sopu ni mezi a mande. - Ministry of Health Zambia",
            },
        }
        return tips.get(tip_type, {}).get(lang, tips.get(tip_type, {}).get("en", ""))

    @staticmethod
    def general_notification(message_en: str, lang: str = "en") -> str:
        translations = {
            "bem": "Icheni mukwai. Umulandu: " + message_en,
            "nyj": "Moni. Uthenga: " + message_en,
            "tog": "Mwami. Twakwezya: " + message_en,
            "loz": "Mwa. Mulao: " + message_en,
        }
        return translations.get(lang, message_en)
