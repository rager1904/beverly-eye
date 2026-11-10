'use client';

import { api } from '@/lib/api-client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles, Save, Mic, FileText, Plus, Check, Loader2, Eye, Stethoscope, Search } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '@/lib/auth';
import { VoiceRecorder } from '@/components/provider/VoiceRecorder';
import { format } from 'date-fns';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { usePatientSearch } from '@/hooks/usePatientFlow';
import type { PatientSearchResult } from '@/types';

interface ClinicalNote {
  id: string;
  patient_id: string;
  note_type: string;
  title?: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  status: string;
  authored_by: string;
  authored_datetime: string;
}

type NoteSpecialty = 'general' | 'eye' | 'dental';

const NOTE_TEMPLATES: Record<NoteSpecialty, {
  label: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}> = {
  general: {
    label: 'General Clinic',
    subjective: 'Presenting complaint; onset and progression; relevant symptoms; past medical and surgical history; current medications; allergies; family and social history.',
    objective: 'Vital signs; relevant general examination findings; focused system examination; available point-of-care tests, laboratory results or imaging.',
    assessment: 'Working diagnosis and differential; relevant severity or risk factors; problems requiring follow-up.',
    plan: 'Treatment and medication; investigations; counselling; referrals; follow-up interval; return precautions.',
  },
  eye: {
    label: 'Eye Clinic',
    subjective: 'Presenting eye complaint; laterality (right / left / both); onset and progression; blurred or reduced vision; eye pain; redness; photophobia; flashes or floaters; discharge; glasses/contact lens use; ocular and medical history.',
    objective: 'Visual acuity OD / OS (with correction and pinhole); pupils / RAPD; extraocular movements; visual fields; IOP (mmHg); external and slit-lamp exam; anterior chamber; fluorescein; dilated fundus / optic nerve findings.',
    assessment: 'Eye diagnosis and laterality; severity / stage; differential diagnosis; urgent red flags or vision-threatening concerns.',
    plan: 'Treatment and eye medication (drug, strength, eye, frequency, duration); procedure; referral; eye-safety advice; follow-up interval; return precautions.',
  },
  dental: {
    label: 'Dentistry / Oral Health',
    subjective: 'Dental complaint and tooth / site (FDI notation if known); onset and pain score; sensitivity to hot / cold or biting; swelling, bleeding, discharge or trauma; chewing difficulty; prior dental treatment; medical history and allergies.',
    objective: 'Vitals; extraoral and intraoral findings; tooth number / surface; caries; percussion and mobility; periodontal / gingival findings; oral mucosa; occlusion; dental imaging and key findings.',
    assessment: 'Dental diagnosis; tooth / site; pulpal, periapical or periodontal diagnosis; severity; differential diagnosis.',
    plan: 'Consent; treatment performed or planned (restoration, extraction, endodontics, periodontal care); local anaesthetic / materials; medication; oral-health advice; referral; follow-up and return precautions.',
  },
};

type SOAPFields = 'subjective' | 'objective' | 'assessment' | 'plan';
type MarkerDef = { keyword: string; field: SOAPFields };

const SOAP_DICTIONARY: Record<string, { field: SOAPFields; weight: number }[]> = {
  subjective: [
    { field: 'subjective', weight: 3 }, { field: 'subjective', weight: 3 },
    { field: 'subjective', weight: 2 },
  ],
};

const SOAP_CLASSIFIER: {
  category: string;
  terms: string[];
  patterns: RegExp[];
  field: SOAPFields;
  weight: number;
  note: string;
}[] = [
  // ── SUBJECTIVE ──
  { category: 'chief complaint', terms: [
    'chief complaint', 'cc:', 'reason for visit', 'presenting complaint',
    'main concern', 'complains of', 'c/o', 'reports', 'complaint',
    'history of present illness', 'hpi',
  ], patterns: [], field: 'subjective', weight: 3, note: 'chief complaint / HPI openers' },
  { category: 'symptom descriptors', terms: [
    'headache', 'dizziness', 'pain', 'fever', 'cough', 'nausea', 'vomiting',
    'diarrhea', 'fatigue', 'weakness', 'chest pain', 'sob', 'dyspnea',
    'palpitations', 'swelling', 'rash', 'itching', 'burning', 'numbness',
    'tingling', 'blurred vision', 'vision loss', 'reduced vision', 'eye pain',
    'red eye', 'redness', 'photophobia', 'floaters', 'flashes', 'tearing',
    'eye discharge', 'toothache', 'tooth pain', 'dental pain', 'tooth sensitivity',
    'gum pain', 'gum swelling', 'oral swelling', 'hearing loss', 'tinnitus', 'anxiety',
    'depression', 'insomnia', 'loss of appetite', 'weight loss', 'weight gain',
    'sweating', 'chills', 'rigors', 'myalgia', 'arthralgia', 'back pain',
    'abdominal pain', 'constipation', 'blood in stool', 'dysuria',
    'frequency', 'urgency', 'vaginal discharge', 'penile discharge',
    'sore throat', 'runny nose', 'congestion', 'sneezing', 'wheezing',
    'hemoptysis', 'syncope', 'seizure', 'confusion', 'feverish',
  ], patterns: [
    /(?:patient\s+)?reports?\s+\w+/i, /complains?\s+of/i,
    /since\s+(last|yesterday|\d+\s*(day|week|month|year)s?)/i,
    /\b(?:days?|weeks?|months?)\s+ago\b/i,
  ], field: 'subjective', weight: 2, note: 'common symptoms' },
  { category: 'pmh / history', terms: [
    'past medical history', 'pmh', 'pmhx', 'past surgical history', 'psh',
    'medications', 'meds:', 'allergies', 'allergy', 'nkda', 'social history',
    'family history', 'fhx', 'smoking', 'alcohol', 'tobacco', 'substance use',
    'immunizations', 'vaccinations', 'history of',
  ], patterns: [], field: 'subjective', weight: 2, note: 'patient history' },

  // ── OBJECTIVE ──
  { category: 'vitals', terms: [
    'vitals', 'vital signs', 'bp', 'blood pressure', 'hr', 'heart rate',
    'pulse', 'temp', 'temperature', 'rr', 'respiratory rate', 'spo2',
    'o2 sat', 'oxygen saturation', 'bmi', 'weight', 'height',
  ], patterns: [
    /\bbp\s*\d{2,3}\s*\/\s*\d{2,3}/, /\bhr\s*\d{2,3}/, /\bpulse\s*\d{2,3}/,
    /\btemp\s*\d{2,3}/, /\brr\s*\d{2,3}/, /\bspo2\s*\d{2,3}/,
    /\bo2\s*sat\s*\d{2,3}/, /\bweight\s*\d/, /\bheight\s*\d/,
  ], field: 'objective', weight: 3, note: 'vital sign measurements' },
  { category: 'physical exam', terms: [
    'physical exam', 'pe:', 'general appearance', 'heent', 'neck',
    'chest', 'lungs', 'cardiovascular', 'cv:', 'abdomen', 'extremities',
    'neuro', 'skin', 'musculoskeletal', 'rectal', 'pelvic', 'gu:',
    'fundoscopic', 'fundus', 'visual acuity', 'visual fields', 'pinhole', 'rapd',
    'intraocular pressure', ' iop', 'tonometry', 'slit lamp', 'anterior chamber',
    'fluorescein', 'optic nerve', 'retina', 'extraocular movements',
    'tooth number', 'fdI', 'caries', 'cavity', 'gingiva', 'gingival', 'periodontal',
    'percussion', 'tooth mobility', 'oral mucosa', 'occlusion', 'probing depth',
    'cranial nerves', 'motor', 'sensory', 'reflexes',
    'edema', 'clubbing', 'cyanosis', 'lymph nodes', 'breast exam',
    ' oral mucosa', 'pharynx', 'tympanic', 'auscultation', 'palpation',
    'percussion', 'inspection', 'fundal height',
  ], patterns: [
    /^(?:exam|findings|physical|objective):?$/im,
    /\b(?:clear|diminished|normal|abnormal)\s+(?:lung|breath|heart|bowel)\s+sounds/i,
    /\b(?:regular|irregular)\s+rate\s+and\s+rhythm/i,
  ], field: 'objective', weight: 3, note: 'physical examination findings' },
  { category: 'labs / imaging', terms: [
    'lab', 'labs', 'laboratory', 'cbc', 'fbc', 'electrolytes', 'lfts',
    'rfts', 'blood sugar', 'hba1c', 'lipid profile', 'urinalysis',
    'ua:', 'culture', 'sensitivity', 'x-ray', 'xray', 'chest xray',
    'cxr', 'ecg', 'ekg', 'ultrasound', 'ct', 'mri', 'echo',
    'imaging', 'wbc', 'hgb', 'hct', 'platelets', 'crp', 'esr',
    'malaria smear', 'bfmp', 'rpr', 'vdrl', 'hiv test', 'blood culture',
    'sputum', 'gram stain', 'afb',
  ], patterns: [
    /\b(?:wbc|hgb|hct|plt|crp|esr|na|k|cl|hco3|bun|cr|lfts?)\s*\d/i,
  ], field: 'objective', weight: 3, note: 'laboratory / imaging results' },

  // ── ASSESSMENT ──
  { category: 'diagnoses', terms: [
    'diagnosis', 'diagnoses', 'differential', 'assessment', 'impression',
    'problem list', 'formulation', 'working diagnosis', 'primary diagnosis',
    'secondary diagnosis', 'comorbidity',
  ], patterns: [], field: 'assessment', weight: 3, note: 'diagnosis headers' },
  { category: 'common conditions', terms: [
    'hypertension', 'htn', 'diabetes', 'dm', 'asthma', 'copd', 'malaria',
    'tb', 'tuberculosis', 'hiv', 'aids', 'uti', 'urinary tract infection',
    'pneumonia', 'anemia', 'sickle cell', 'ssd', 'scd', 'sickle cell disease',
    'malnutrition', 'kwashiorkor', 'marasmus', 'diarrheal disease',
    'cholera', 'typhoid', 'dengue', 'measles', 'meningitis', 'sepsis',
    'cellulitis', 'abscess', 'wound infection', 'conjunctivitis', 'cataract',
    'glaucoma', 'uveitis', 'keratitis', 'retinopathy', 'refractive error',
    'pulpitis', 'periodontitis', 'gingivitis', 'dental abscess', 'periapical',
    'caries', 'tooth fracture', 'malocclusion', 'std', 'sti',
    'gonorrhea', 'syphilis', 'hepatitis', 'cirrhosis', 'heart failure',
    'chf', 'cad', 'ckd', 'arthritis', 'gout', 'asthma', 'allergic rhinitis',
    'gastroenteritis', 'peptic ulcer', 'gastritis', 'appendicitis',
    'cholecystitis', 'pancreatitis', 'pyelonephritis', 'prostatitis',
    'pid', 'ectopic', 'miscarriage', 'pre-eclampsia', 'eclampsia',
    'gestational diabetes', 'preterm labor', 'depression', 'psychosis',
    'schizophrenia', 'bipolar', 'epilepsy', 'seizure disorder',
    'parkinsons', 'dementia', 'cva', 'stroke', 'tia',
  ], patterns: [
    /^(?:rule\s*out|r\/o|likely|possible|probable)\b/i,
    /(?:stage|grade|class)\s+\d/i, /\bcontrolled\b/i, /\buncontrolled\b/i,
    /\b(?:mild|moderate|severe)\s+(?:hypertension|asthma|anemia|pain)/i,
  ], field: 'assessment', weight: 2, note: 'specific disease conditions' },
  { category: 'severity / staging', terms: [
    'stage', 'staging', 'grade', 'severity', 'classification',
    'well-controlled', 'uncontrolled', 'stable', 'unstable',
    'improving', 'worsening', 'resolved', 'persistent', 'acute',
    'chronic', 'exacerbation', 'remission', 'relapse',
  ], patterns: [], field: 'assessment', weight: 1, note: 'severity / progression' },

  // ── PLAN ──
  { category: 'medications', terms: [
    'medication', 'medications', 'meds', 'prescribe', 'prescription',
    'dosage', 'dose', 'tablet', 'capsule', 'syrup', 'suspension',
    'injection', 'iv', 'infusion', 'topical', 'ointment', 'cream',
    'inhaler', 'nebulizer', 'mg', 'mcg', 'gram', 'liter',
    'daily', 'bid', 'tid', 'qid', 'q6h', 'q8h', 'q12h', 'hs', 'prn',
    'amlodipine', 'enalapril', 'nifedipine', 'losartan', 'metformin',
    'glibenclamide', 'insulin', 'artemether', 'lumefantrine', 'coartem',
    'amoxicillin', 'ceftriaxone', 'azithromycin', 'doxycycline',
    'ciprofloxacin', 'metronidazole', 'fluconazole', 'paracetamol',
    'ibuprofen', 'diclofenac', 'morphine', 'tramadol', 'omeprazole',
    'furosemide', 'spironolactone', 'arv', 'tenofovir', 'nevirapine',
    'efavirenz', 'zinc', 'ors', 'vitamin a', 'vitamin', 'iron',
    'folic acid', 'multivitamin',
  ], patterns: [
    /\b\d+\s*(?:mg|mcg|g|ml|l|iu)\b/, /\b(?:po|im|iv|sc|sl|pr|inh)\b/i,
    /^\s*[-\*]\s*\w+/m,
  ], field: 'plan', weight: 3, note: 'medication names / dosing' },
  { category: 'procedures / referrals', terms: [
    'procedure', 'surgery', 'operation', 'refer', 'referral', 'eye drops',
    'ophthalmic', 'topical eye', 'extraction', 'restoration', 'root canal',
    'endodontic', 'scaling', 'polishing', 'local anaesthetic', 'local anesthetic',
    'admit', 'admission', 'discharge', 'transfer', 'consult',
    'specialist', 'physiotherapy', 'occupational therapy',
    'dietician', 'nutrition', 'counseling', 'health education',
    'follow up', 'follow-up', 'f/u', 'return to clinic',
    'monitor', 'monitoring', 'observation', 'reassess',
    'review in', 'schedule', 'appointment', 'book',
  ], patterns: [
    /\bfollow\s*[- ]*up\b/i, /\bf\/u\b/i, /\breturn\s+(?:to|in)\b/i,
    /\breview\s+in\s+\d+/i, /\brefer\s+to\b/i,
  ], field: 'plan', weight: 3, note: 'procedures / referrals / follow-up' },
  { category: 'patient education', terms: [
    'patient education', 'counseling', 'advice', 'advise', 'instructions',
    'discharge instructions', 'lifestyle modification', 'diet',
    'exercise', 'salt restriction', 'fluid restriction', 'wound care',
    'dressing', 'safety net', 'when to return', 'danger signs',
    'family planning', 'breastfeeding', 'nutrition counseling',
  ], patterns: [], field: 'plan', weight: 2, note: 'patient instructions' },

  // ── GREETINGS / META (routes to subjective) ──
  { category: 'greetings', terms: [
    'hello', 'hi', 'good morning', 'good afternoon', 'doctor',
    'nurse', 'clinical officer', 'my name is', 'i am',
  ], patterns: [], field: 'subjective', weight: 1, note: 'greetings / introductions' },
];

function classifyLine(line: string): SOAPFields | null {
  const l = line.toLowerCase().trim();
  if (!l) return null;

  const scores: Record<SOAPFields, number> = {
    subjective: 0, objective: 0, assessment: 0, plan: 0,
  };

  for (const entry of SOAP_CLASSIFIER) {
    let matched = false;
    for (const term of entry.terms) {
      if (l.includes(term.toLowerCase())) { matched = true; break; }
    }
    if (!matched) {
      for (const pattern of entry.patterns) {
        if (pattern.test(l)) { matched = true; break; }
      }
    }
    if (matched) {
      scores[entry.field] += entry.weight;
    }
  }

  const best = (Object.entries(scores) as [SOAPFields, number][]).reduce((a, b) =>
    b[1] > a[1] ? b : a[1] > b[1] ? a : a[0] < b[0] ? a : b
  );
  return best[1] > 0 ? best[0] : null;
}

function parseSOAPText(text: string): { subjective: string; objective: string; assessment: string; plan: string } | null {
  const lower = text.toLowerCase();
  const markers: MarkerDef[] = [
    { keyword: 'subjective', field: 'subjective' },
    { keyword: 'subject', field: 'subjective' },
    { keyword: 'objective', field: 'objective' },
    { keyword: 'object', field: 'objective' },
    { keyword: 'assessment', field: 'assessment' },
    { keyword: 'plan', field: 'plan' },
  ];

  const positions: { index: number; field: SOAPFields; marker: string }[] = [];
  let searchFrom = 0;
  while (searchFrom < lower.length) {
    let best: { index: number; field: SOAPFields; marker: string } | null = null;
    for (const m of markers) {
      const idx = lower.indexOf(m.keyword, searchFrom);
      if (idx !== -1 && (!best || idx < best.index)) {
        best = { index: idx, field: m.field, marker: m.keyword };
      }
    }
    if (!best) break;
    positions.push(best);
    searchFrom = best.index + best.marker.length;
  }

  if (positions.length >= 2) {
    const result: Record<SOAPFields, string> = {
      subjective: '', objective: '', assessment: '', plan: '',
    };
    for (let i = 0; i < positions.length; i++) {
      const pos = positions[i]!;
      const start = pos.index + pos.marker.length;
      const end = i + 1 < positions.length ? positions[i + 1]!.index : text.length;
      const sectionText = text.slice(start, end).trim();
      if (sectionText) {
        const existing = result[pos.field];
        result[pos.field] = existing ? existing + '\n' + sectionText : sectionText;
      }
    }
    const first = positions[0]!;
    if (first.index > 0) {
      const preamble = text.slice(0, first.index).trim();
      if (preamble) result.subjective = preamble + '\n' + result.subjective;
    }
    return result;
  }

  // No keyword markers found — classify line-by-line by content
  const lines = text.split('\n');
  const classified: Record<SOAPFields, string[]> = {
    subjective: [], objective: [], assessment: [], plan: [],
  };
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const field = classifyLine(trimmed);
    if (field) {
      classified[field].push(trimmed);
    } else {
      classified.subjective.push(trimmed);
    }
  }
  const hasContent = (f: SOAPFields) => classified[f].length > 0;
  if (!hasContent('subjective') && !hasContent('objective') && !hasContent('assessment') && !hasContent('plan')) {
    return null;
  }
  return {
    subjective: classified.subjective.join('\n'),
    objective: classified.objective.join('\n'),
    assessment: classified.assessment.join('\n'),
    plan: classified.plan.join('\n'),
  };
}

function formatDate(iso: string) {
  try {
    return format(new Date(iso), 'MMM d, yyyy HH:mm');
  } catch {
    return iso;
  }
}

export default function ClinicalNotesPage() {
  const token = useAuthStore((s) => s.accessToken);

  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [noteSpecialty, setNoteSpecialty] = useState<NoteSpecialty>('general');
  const [patientQuery, setPatientQuery] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<PatientSearchResult | null>(null);
  const [selectedEncounterId, setSelectedEncounterId] = useState<string | null>(null);
  const [associationLoading, setAssociationLoading] = useState(false);
  const initialUrlContextHandled = useRef(false);
  const urlContextRequestId = useRef(0);
  const patientSearch = usePatientSearch(patientQuery);

  const [subjective, setSubjective] = useState('');
  const [objective, setObjective] = useState('');
  const [assessment, setAssessment] = useState('');
  const [plan, setPlan] = useState('');
  const [title, setTitle] = useState('');

  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await api.get<{ items: ClinicalNote[] }>('/emr/notes');
      setNotes(data.items);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not load clinical notes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) fetchNotes();
  }, [token, fetchNotes]);

  const selectedNote = notes.find((n) => n.id === selectedNoteId);

  const handleSelectNote = useCallback((note: ClinicalNote) => {
    urlContextRequestId.current += 1;
    setAssociationLoading(false);
    setSelectedNoteId(note.id);
    setSelectedEncounterId(null);
    const titleLower = note.title?.toLowerCase() ?? '';
    setNoteSpecialty(titleLower.includes('dental') ? 'dental' : titleLower.includes('eye') || titleLower.includes('ophthalm') ? 'eye' : 'general');
    setSelectedPatient(null);
    setPatientQuery('');
    setTitle(note.title || '');
    setSubjective(note.subjective || '');
    setObjective(note.objective || '');
    setAssessment(note.assessment || '');
    setPlan(note.plan || '');
    setAiSuggestion('');
  }, []);

  const handleNewNote = () => {
    urlContextRequestId.current += 1;
    setAssociationLoading(false);
    setSelectedNoteId(null);
    setNoteSpecialty('general');
    setSelectedPatient(null);
    setSelectedEncounterId(null);
    setPatientQuery('');
    setTitle('');
    setSubjective('');
    setObjective('');
    setAssessment('');
    setPlan('');
    setAiSuggestion('');
  };

  useEffect(() => {
    if (!token || initialUrlContextHandled.current) return;

    const params = new URLSearchParams(window.location.search);
    const noteId = params.get('note');
    const encounterId = params.get('encounter');
    if (!noteId && !encounterId) {
      initialUrlContextHandled.current = true;
      return;
    }

    let active = true;
    const requestId = ++urlContextRequestId.current;
    setAssociationLoading(true);
    void (async () => {
      try {
        if (noteId) {
          const note = await api.get<ClinicalNote>(`/emr/notes/${encodeURIComponent(noteId)}`);
          if (active && requestId === urlContextRequestId.current) {
            initialUrlContextHandled.current = true;
            handleSelectNote(note);
          }
          return;
        }

        // The encounter is the source of truth for the patient association.
        const encounter = await api.get<{ id: string; patient_id: string }>(`/emr/encounters/${encodeURIComponent(encounterId!)}`);
        const patient = await api.get<PatientSearchResult>(`/emr/patients/${encodeURIComponent(encounter.patient_id)}`);
        if (active && requestId === urlContextRequestId.current) {
          initialUrlContextHandled.current = true;
          setSelectedPatient(patient);
          setSelectedEncounterId(encounter.id);
          setPatientQuery('');
        }
      } catch (error) {
        if (active && requestId === urlContextRequestId.current) {
          initialUrlContextHandled.current = true;
          toast.error(error instanceof Error ? error.message : 'Could not load the encounter patient');
        }
      } finally {
        if (active && requestId === urlContextRequestId.current) setAssociationLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [token, handleSelectNote]);

  const handleSave = async () => {
    const noteId = selectedNoteId;
    const patientId = selectedPatient?.id;
    const encounterId = selectedEncounterId;
    if (!noteId && !patientId) {
      toast.error('Select a patient before saving a new clinical note');
      return;
    }
    if (!subjective && !objective && !assessment && !plan) {
      toast.error('Add content before saving');
      return;
    }
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        title: title || `${NOTE_TEMPLATES[noteSpecialty].label} SOAP Note`,
        subjective,
        objective,
        assessment,
        plan,
      };
      if (!noteId && patientId) {
        body.note_type = 'SOAP';
        body.patient_id = patientId;
        if (encounterId) body.encounter_id = encounterId;
      }

      if (noteId) {
        await api.patch(`/emr/notes/${noteId}`, body);
      } else {
        await api.post('/emr/notes', body);
      }
      toast.success(noteId ? 'Note updated' : 'Note saved');
      await fetchNotes();
      if (!noteId) handleNewNote();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save clinical note');
    } finally {
      setSaving(false);
    }
  };

  const handleAiAssist = async () => {
    if (!subjective && !objective) {
      toast.error('Add at least subjective and objective first');
      return;
    }
    setAiLoading(true);
    try {
      const res = await fetch('/api/v1/agents/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: `Draft a specialty-aware SOAP assessment and plan for a ${NOTE_TEMPLATES[noteSpecialty].label} visit using only the supplied information. Do not invent examination findings, diagnoses, laterality, tooth numbers, or treatment. Clearly flag missing information and keep the clinician responsible for review.\n\nSubjective: ${subjective}\n\nObjective: ${objective}\n\nAssessment so far: ${assessment}\n\nCurrent plan: ${plan}`,
          conversation_id: `soap-${Date.now()}`,
          agent: 'clinical_documentation',
          metadata: { action: 'soap_note', specialty: noteSpecialty, transcript: `Subjective: ${subjective}\nObjective: ${objective}\nAssessment: ${assessment}\nPlan: ${plan}` },
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiSuggestion(data.response || data.message || '');
      } else {
        const err = await res.json().catch(() => ({ detail: 'AI assist failed' }));
        toast.error(err.detail || 'AI assist failed');
      }
    } catch {
      toast.error('AI assist unavailable');
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
            <h1 className="text-2xl font-bold">Eye &amp; Dental Clinical Notes</h1>
            <p className="text-sm text-muted-foreground">SOAP documentation for the General, Eye, and Dental departments.</p>
        </div>
        <Button onClick={handleNewNote} disabled={!selectedNoteId && !subjective && !objective && !assessment && !plan}>
          <Plus className="h-4 w-4 mr-1" />New Note
        </Button>
      </div>

      <Card>
        <CardContent className="grid gap-4 p-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Patient {selectedNoteId ? '' : '*'}</label>
            {associationLoading ? (
              <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">Loading encounter patient…</p>
            ) : selectedPatient ? (
              <div className="flex min-h-10 items-center justify-between rounded-md border px-3 py-2">
                <span className="text-sm font-medium">
                  {selectedPatient.first_name} {selectedPatient.last_name}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {selectedPatient.nrc_number || selectedPatient.phone}
                  </span>
                  {selectedEncounterId && (
                    <span className="ml-2 text-xs text-muted-foreground">· linked to selected encounter</span>
                  )}
                </span>
                <Button size="sm" variant="ghost" onClick={() => {
                  setSelectedPatient(null);
                  setSelectedEncounterId(null);
                }}>
                  Change
                </Button>
              </div>
            ) : selectedNote ? (
              <p className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
                Existing note is linked to patient record {selectedNote.patient_id.slice(0, 8)}…
              </p>
            ) : (
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={patientQuery}
                  onChange={(event) => setPatientQuery(event.target.value)}
                  placeholder="Search name, NRC, or phone (type at least 2 characters)"
                />
                {patientQuery.trim().length >= 2 && (
                  <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-md border bg-background shadow-lg">
                    {patientSearch.isLoading ? (
                      <p className="p-3 text-sm text-muted-foreground">Searching patients…</p>
                    ) : (patientSearch.data?.items.length ?? 0) === 0 ? (
                      <p className="p-3 text-sm text-muted-foreground">No matching patients found.</p>
                    ) : (
                      patientSearch.data?.items.map((patient) => (
                        <button
                          key={patient.id}
                          type="button"
                          className="block w-full px-3 py-2 text-left hover:bg-muted"
                          onClick={() => {
                            setSelectedPatient(patient);
                            setPatientQuery('');
                          }}
                        >
                          <span className="block text-sm font-medium">
                            {patient.first_name} {patient.last_name}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {patient.nrc_number || 'No NRC'} · {patient.phone}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Clinical note template</label>
            <Select
              value={noteSpecialty}
              onValueChange={(value) => setNoteSpecialty(value as NoteSpecialty)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General Clinic</SelectItem>
                <SelectItem value="eye">Eye Clinic</SelectItem>
                <SelectItem value="dental">Dentistry / Oral Health</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {noteSpecialty === 'eye'
                ? 'Prompts cover laterality, visual acuity, pupils, eye movements, IOP, slit-lamp and fundus findings.'
                : noteSpecialty === 'dental'
                  ? 'Prompts cover tooth/site, pain, oral examination, periodontal findings, treatment and follow-up.'
                  : 'Prompts cover general history, examination, assessment, investigations, and follow-up.'}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <FileText className="h-4 w-4" /> Saved Notes
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="flex items-center justify-center p-6">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : notes.length === 0 ? (
                <p className="text-xs text-muted-foreground p-4">No notes yet. Record or type a note and save it.</p>
              ) : (
                <div className="divide-y max-h-[600px] overflow-y-auto">
                  {notes.map((note) => (
                    <button
                      key={note.id}
                      onClick={() => handleSelectNote(note)}
                      className={`w-full text-left p-3 hover:bg-muted/50 transition-colors ${
                        selectedNoteId === note.id ? 'bg-muted' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium truncate">
                          {note.title || 'SOAP Note'}
                        </span>
                        <Badge variant="outline" className="text-[10px]">
                          {note.status === 'final' ? <Check className="h-3 w-3 mr-0.5" /> : null}
                          {note.status}
                        </Badge>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {formatDate(note.authored_datetime)}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3 space-y-4">
          <VoiceRecorder
            onTranscriptionComplete={(text) => {
              const parsed = parseSOAPText(text);
              if (parsed) {
                if (parsed.subjective) setSubjective((prev) => prev + (prev ? '\n' : '') + parsed.subjective);
                if (parsed.objective) setObjective((prev) => prev + (prev ? '\n' : '') + parsed.objective);
                if (parsed.assessment) setAssessment((prev) => prev + (prev ? '\n' : '') + parsed.assessment);
                if (parsed.plan) setPlan((prev) => prev + (prev ? '\n' : '') + parsed.plan);
                toast.success('Transcription routed to SOAP fields');
              } else {
                setSubjective((prev) => prev + (prev ? '\n' : '') + text);
                toast.success('Transcription added to Subjective');
              }
            }}
          />

          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <div className="flex items-center gap-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  {noteSpecialty === 'eye' ? <Eye className="h-4 w-4" /> : <Stethoscope className="h-4 w-4" />}
                  {NOTE_TEMPLATES[noteSpecialty].label} SOAP Note
                </CardTitle>
                {selectedNote && <Badge variant="secondary">{selectedNote.note_type}</Badge>}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleAiAssist} disabled={aiLoading}>
                  <Sparkles className={`h-4 w-4 mr-1 ${aiLoading ? 'animate-spin' : ''}`} />
                  AI Assist
                </Button>
                <Button size="sm" onClick={handleSave} disabled={saving || associationLoading}>
                  {saving ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-1" />
                  )}
                  {selectedNoteId ? 'Update' : 'Save'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Note title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full text-sm border-b border-border pb-1 focus:outline-none focus:border-primary bg-transparent"
                />
              </div>

              <Tabs defaultValue="edit">
                <TabsList className="mb-4">
                  <TabsTrigger value="edit">Edit</TabsTrigger>
                  <TabsTrigger value="preview">Preview</TabsTrigger>
                  {aiSuggestion && (
                    <TabsTrigger value="ai-suggest">
                      AI Suggestion <Badge variant="info" className="ml-1 text-xs">New</Badge>
                    </TabsTrigger>
                  )}
                </TabsList>

                <TabsContent value="edit" className="space-y-3">
                  <div>
                    <label className="text-xs font-medium mb-1 block text-muted-foreground flex items-center gap-1">
                      <Mic className="h-3 w-3" /> Subjective
                    </label>
                    <Textarea
                      placeholder={NOTE_TEMPLATES[noteSpecialty].subjective}
                      value={subjective}
                      onChange={(e) => setSubjective(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1 block text-muted-foreground">Objective</label>
                    <Textarea
                      placeholder={NOTE_TEMPLATES[noteSpecialty].objective}
                      value={objective}
                      onChange={(e) => setObjective(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1 block text-muted-foreground">Assessment</label>
                    <Textarea
                      placeholder={NOTE_TEMPLATES[noteSpecialty].assessment}
                      value={assessment}
                      onChange={(e) => setAssessment(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1 block text-muted-foreground">Plan</label>
                    <Textarea
                      placeholder={NOTE_TEMPLATES[noteSpecialty].plan}
                      value={plan}
                      onChange={(e) => setPlan(e.target.value)}
                      rows={3}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="preview" className="space-y-3 prose prose-sm max-w-none">
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground">S:</h4>
                    <p className="text-sm">{subjective || 'No data entered'}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground">O:</h4>
                    <p className="text-sm">{objective || 'No data entered'}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground">A:</h4>
                    <p className="text-sm">{assessment || 'No data entered'}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground">P:</h4>
                    <p className="text-sm">{plan || 'No data entered'}</p>
                  </div>
                </TabsContent>

                {aiSuggestion && (
                  <TabsContent value="ai-suggest">
                    <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="h-4 w-4 text-blue-600" />
                        <span className="font-medium text-blue-800">AI-Suggested Assessment & Plan</span>
                      </div>
                      <p className="text-sm text-blue-900 whitespace-pre-wrap">{aiSuggestion}</p>
                      <div className="flex gap-2 mt-3">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            const lines = aiSuggestion.split('\n');
                            const aLines: string[] = [];
                            const pLines: string[] = [];
                            let inPlan = false;
                            for (const line of lines) {
                              if (/^plan/i.test(line.trim())) { inPlan = true; }
                              if (inPlan) pLines.push(line);
                              else aLines.push(line);
                            }
                            setAssessment(aLines.join('\n').replace(/^assessment/i, '').trim());
                            setPlan(pLines.join('\n').replace(/^plan/i, '').trim());
                            setAiSuggestion('');
                            toast.success('Applied to Assessment & Plan');
                          }}
                        >
                          Apply to Assessment & Plan
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setAiSuggestion('')}>Dismiss</Button>
                      </div>
                    </div>
                  </TabsContent>
                )}
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
