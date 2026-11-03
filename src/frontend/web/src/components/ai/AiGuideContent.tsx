'use client';

import { ReactNode } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bot, Microscope, Stethoscope, Pill, ClipboardList, Calendar, BarChart3, Heart, Speech, Ear, Sparkles } from 'lucide-react';

interface Capability {
  icon: ReactNode;
  title: string;
  description: string;
  example: string;
}

interface RoleData { title: string; description: string; capabilities: Capability[] }
const roleData: Record<string, RoleData> = {
  patient: {
    title: 'UbuntuCare AI Assistant for Patients',
    description: 'Your personal health companion. Ask questions about your medications, lab results, appointments, and get health tips in English, Bemba, Nyanja, Tonga, or Lozi.',
    capabilities: [
      { icon: <Pill className="h-5 w-5" />, title: 'Medication Info', description: 'Ask about your current medications, dosage, and schedule.', example: '"What medications am I taking?"' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'Lab Results', description: 'Get plain-language explanations of your lab results.', example: '"Explain my malaria test results."' },
      { icon: <Calendar className="h-5 w-5" />, title: 'Appointments', description: 'Check upcoming appointments and get reminders.', example: '"When is my next appointment?"' },
      { icon: <Sparkles className="h-5 w-5" />, title: 'Health Tips', description: 'Get personalized health tips and prevention advice.', example: '"Health tips for malaria prevention."' },
      { icon: <Speech className="h-5 w-5" />, title: 'Voice Input', description: 'Use your voice to ask questions (speech-to-text).', example: 'Click the mic button and speak your question.' },
      { icon: <Ear className="h-5 w-5" />, title: 'Voice Output', description: 'Hear responses read aloud (text-to-speech).', example: 'Click the speaker icon on any AI response.' },
    ],
  },
  provider: {
    title: 'UbuntuCare AI Assistant for Healthcare Providers',
    description: 'Your clinical decision support tool. Get triage assessments, differential diagnoses, clinical documentation assistance, and Zambia-specific medical guidance.',
    capabilities: [
      { icon: <Stethoscope className="h-5 w-5" />, title: 'Triage Assessment', description: 'Get SATS-based triage assessments for your patients.', example: '"Assess a 45-year-old with chest pain and shortness of breath."' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'Clinical Documentation', description: 'Generate SOAP notes and clinical summaries from your observations.', example: '"Generate a SOAP note for a malaria case."' },
      { icon: <Microscope className="h-5 w-5" />, title: 'Differential Diagnosis', description: 'Get Zambia-specific differential diagnoses considering local epidemiology.', example: '"Differential diagnosis for fever with rash in Lusaka."' },
      { icon: <Calendar className="h-5 w-5" />, title: 'Appointment Management', description: 'Schedule, reschedule, or cancel patient appointments.', example: '"Schedule a follow-up for patient John next week."' },
      { icon: <BarChart3 className="h-5 w-5" />, title: 'Medical Research', description: 'Look up clinical guidelines, drug interactions, and latest evidence.', example: '"What are the current Zambia malaria treatment guidelines?"' },
      { icon: <Speech className="h-5 w-5" />, title: 'Voice Notes', description: 'Dictate clinical notes using voice input (speech-to-text).', example: 'Click the mic button to dictate patient encounters.' },
    ],
  },
  nurse: {
    title: 'UbuntuCare AI Assistant for Nurses',
    description: 'Your nursing workflow assistant. Get triage support, medication guidance, patient education resources, and clinical documentation help.',
    capabilities: [
      { icon: <Stethoscope className="h-5 w-5" />, title: 'Triage Support', description: 'SATS-based triage assessment for walk-in patients.', example: '"Triage a child with fever, cough, and rapid breathing."' },
      { icon: <Pill className="h-5 w-5" />, title: 'Medication Guidance', description: 'Check medication dosages, routes, and administration guidelines.', example: '"What is the correct dosage of oral rehydration salts for a 2-year-old?"' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'Patient Education', description: 'Get patient education materials in local languages.', example: '"Give me malaria prevention advice in Bemba."' },
      { icon: <Calendar className="h-5 w-5" />, title: 'Appointment Management', description: 'Manage patient appointments and follow-up schedules.', example: '"Remind me about overdue immunizations."' },
    ],
  },
  admin: {
    title: 'UbuntuCare AI Assistant for Hospital Administrators',
    description: 'Your administrative intelligence tool. Generate reports, analyze hospital metrics, manage resources, and track public health data.',
    capabilities: [
      { icon: <BarChart3 className="h-5 w-5" />, title: 'Analytics Reports', description: 'Generate hospital performance and utilization reports.', example: '"Show me admission trends this month."' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'MoH Reporting', description: 'Generate Ministry of Health compliance reports.', example: '"Generate the weekly HMIS report."' },
      { icon: <Pill className="h-5 w-5" />, title: 'Resource Management', description: 'Track bed occupancy, supply levels, and staff scheduling.', example: '"What is current bed occupancy?"' },
      { icon: <Heart className="h-5 w-5" />, title: 'Referral Management', description: 'Track patient referrals and transfer logistics.', example: '"Show pending referrals to UTH."' },
    ],
  },
  lab_tech: {
    title: 'UbuntuCare AI Assistant for Laboratory Technicians',
    description: 'Your lab workflow assistant. Get test interpretation guidance, quality control support, and result reporting help.',
    capabilities: [
      { icon: <Microscope className="h-5 w-5" />, title: 'Test Interpretation', description: 'Get guidance on test results and abnormal value significance.', example: '"What does a high malaria parasite density indicate?"' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'Result Reporting', description: 'Generate lab report summaries for clinicians.', example: '"Summarize these CBC results."' },
      { icon: <Pill className="h-5 w-5" />, title: 'Quality Control', description: 'Get QC guidelines and troubleshooting for lab equipment.', example: '"QC troubleshooting for hematology analyzer."' },
    ],
  },
  pharmacist: {
    title: 'UbuntuCare AI Assistant for Pharmacists',
    description: 'Your pharmaceutical intelligence tool. Check drug interactions, manage inventory, verify prescriptions, and access Zambia Essential Medicines List.',
    capabilities: [
      { icon: <Pill className="h-5 w-5" />, title: 'Drug Interactions', description: 'Check for potential drug-drug interactions.', example: '"Check interaction between artemether-lumefantrine and cotrimoxazole."' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'Prescription Verification', description: 'Verify prescription accuracy and dosing.', example: '"Verify this pediatric amoxicillin prescription."' },
      { icon: <BarChart3 className="h-5 w-5" />, title: 'Inventory Management', description: 'Track stock levels and predict reorder needs.', example: '"Which medicines are low in stock?"' },
      { icon: <Sparkles className="h-5 w-5" />, title: 'EML Guidance', description: 'Access Zambia Essential Medicines List recommendations.', example: '"What is the first-line treatment for uncomplicated malaria?"' },
    ],
  },
  public_health: {
    title: 'UbuntuCare AI Assistant for Public Health Officers',
    description: 'Your epidemiological intelligence tool. Track disease outbreaks, analyze surveillance data, generate MoH reports, and manage vaccination campaigns.',
    capabilities: [
      { icon: <BarChart3 className="h-5 w-5" />, title: 'Disease Surveillance', description: 'Analyze disease trends and detect outbreak signals.', example: '"Show malaria trends in Eastern Province this month."' },
      { icon: <Heart className="h-5 w-5" />, title: 'Outbreak Management', description: 'Get outbreak investigation and response guidance.', example: '"Protocol for a suspected cholera outbreak."' },
      { icon: <ClipboardList className="h-5 w-5" />, title: 'MoH/DHIS2 Reporting', description: 'Generate surveillance reports for Ministry of Health.', example: '"Generate the weekly IDSR report."' },
      { icon: <Pill className="h-5 w-5" />, title: 'Vaccination Campaigns', description: 'Plan and track vaccination coverage.', example: '"Show vaccination coverage in rural districts."' },
    ],
  },
};

export function AiGuideContent({ role }: { role: string }) {
  const data: RoleData = roleData[role] ?? roleData.patient!;
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Bot className="h-6 w-6 text-healthcare-green" />
          {data.title}
        </h2>
        <p className="text-muted-foreground mt-1">{data.description}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {data.capabilities.map((cap, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="text-healthcare-green">{cap.icon}</div>
                <CardTitle className="text-base">{cap.title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-sm mb-2">{cap.description}</CardDescription>
              <Badge variant="secondary" className="text-xs font-mono">{cap.example}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Speech className="h-4 w-4" /> Voice Features</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2 text-muted-foreground">
          <p><strong>Speech-to-Text:</strong> Click the microphone button in the chat widget and speak your question. Your voice is transcribed and sent to the AI.</p>
          <p><strong>Text-to-Speech:</strong> Click the speaker icon on any AI response to hear it read aloud. Supports English, Bemba, Nyanja, Tonga, and Lozi.</p>
          <p><strong>Languages:</strong> Ask questions in English, Bemba, Nyanja, Tonga, or Lozi — the AI understands and responds in your preferred language.</p>
        </CardContent>
      </Card>
    </div>
  );
}
