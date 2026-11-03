import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import bem from './bem.json';
import nyj from './nyj.json';
import tog from './tog.json';
import loz from './loz.json';

const resources = {
  en: { translation: en },
  bem: { translation: bem },
  nyj: { translation: nyj },
  tog: { translation: tog },
  loz: { translation: loz },
};

const savedLanguage = typeof window !== 'undefined' ? localStorage.getItem('ubuntucare-lang') : null;

i18n.use(initReactI18next).init({
  resources,
  lng: savedLanguage || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  detection: { order: ['localStorage', 'navigator'], caches: ['localStorage'] },
});

export function changeLanguage(lng: string) {
  i18n.changeLanguage(lng);
  if (typeof window !== 'undefined') localStorage.setItem('ubuntucare-lang', lng);
  document.documentElement.lang = lng;
}

export default i18n;
