'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SoapNoteEditor } from '@/components/provider/SoapNoteEditor';
import { VoiceRecorder } from '@/components/provider/VoiceRecorder';
import Link from 'next/link';
import { Search, FileText, User, Activity, Heart, ClipboardList, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import { useAuthStore } from '@/lib/auth';
import { formatDate, calculateAge } from '@/lib/utils';

interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  address_line?: string;
  city?: string;
  district?: string;
  province?: string;
  allergies?: { allergen: string; severity: string }[];
  chronicConditions?: { problem_name: string }[];
  nupn?: string;
}

interface Encounter {
  id: string;
  encounter_type: string;
  encounter_datetime: string;
  chief_complaint?: string;
  diagnosis?: string;
  provider_name?: string;
  status: string;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  heart_rate?: number;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
}

interface LabResult {
  id: string;
  order_description: string;
  result_value?: string;
  result_unit?: string;
  reference_range_low?: string;
  reference_range_high?: string;
  interpretation?: string;
  performed_datetime?: string;
  status: string;
}

export default function EMRPage() {
  const router = useRouter();
  const [chatOpen, setChatOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [labs, setLabs] = useState<LabResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);

  const token = useAuthStore((s) => s.accessToken);
  const authHeaders = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const searchPatients = useCallback(async () => {
    if (!searchQuery.trim() || !token) return;
    setSearching(true);
    setShowSearchResults(true);
    try {
      const res = await fetch(`/api/v1/emr/patients?query=${encodeURIComponent(searchQuery)}`, { headers: authHeaders });
      if (res.ok) {
        const data = await res.json();
        setPatients(data.items || data.data || data.patients || []);
      }
    } catch {
      // silently fail
    } finally {
      setSearching(false);
    }
  }, [searchQuery, token]);

  const loadPatient = useCallback(async (patient: Patient) => {
    setSelectedPatient(patient);
    setLoading(true);
    setShowSearchResults(false);
    const opts = { headers: authHeaders };
    try {
      const [encRes, labsRes] = await Promise.all([
        fetch(`/api/v1/emr/encounters?patient_id=${patient.id}`, opts),
        fetch(`/api/v1/emr/orders?patient_id=${patient.id}`, opts),
      ]);
      if (encRes.ok) {
        const data = await encRes.json();
        setEncounters(data.items || data.data || data.encounters || []);
      }
      if (labsRes.ok) {
        const data = await labsRes.json();
        setLabs(data.items || data.data || data.orders || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [encounters, token]);

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h1 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
          <FileText className="h-5 w-6 sm:h-6 sm:w-6 text-healthcare-blue shrink-0" />
          <span className="truncate">Electronic Medical Records</span>
        </h1>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <Input
          placeholder="Search by patient name, NUPN, or national ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') searchPatients(); }}
          className="pl-10 h-10 sm:h-12 text-sm sm:text-base"
        />
        {showSearchResults && (
          <Card className="absolute top-full left-0 right-0 z-50 mt-1 max-h-64 overflow-y-auto shadow-lg">
            <CardContent className="p-2">
              {searching ? (
                <div className="flex items-center justify-center p-4"><Loader2 className="h-5 w-5 animate-spin" /></div>
              ) : patients.length === 0 ? (
                <p className="text-sm text-muted-foreground p-2 text-center">No patients found</p>
              ) : (
                patients.map((p) => (
                  <button
                    key={p.id}
                    className="w-full text-left p-2 rounded hover:bg-accent flex items-center gap-3 text-sm"
                    onClick={() => loadPatient(p)}
                  >
                    <div className="w-8 h-8 rounded-full bg-healthcare-green/10 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-healthcare-green">{p.first_name?.[0]}{p.last_name?.[0]}</span>
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{p.first_name} {p.last_name}</p>
                      <p className="text-xs text-muted-foreground truncate">{p.district || p.city || ''} {p.phone || ''}</p>
                    </div>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {!selectedPatient ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <User className="h-12 w-12 text-muted-foreground/30 mb-3" />
            <p className="text-lg font-medium">Search for a patient</p>
            <p className="text-sm text-muted-foreground">Type a name or ID above to view medical records</p>
            <Button variant="outline" className="mt-4" asChild>
              <Link href="/patient/register">Register New Patient</Link>
            </Button>
          </CardContent>
        </Card>
      ) : loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <div className="grid gap-4 sm:gap-6 grid-cols-1 lg:grid-cols-3">
          <div className="space-y-4 sm:space-y-6">
            <Card>
              <CardHeader className="p-3 sm:p-4">
                <CardTitle className="text-base sm:text-lg flex items-center gap-2">
                  <User className="h-4 w-5 sm:h-5 sm:w-5 text-healthcare-blue shrink-0" />Patient Information
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 sm:p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-healthcare-green/10 flex items-center justify-center shrink-0">
                    <span className="text-lg sm:text-2xl font-bold text-healthcare-green">
                      {selectedPatient.first_name?.[0]}{selectedPatient.last_name?.[0]}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-lg sm:text-xl font-bold truncate">{selectedPatient.first_name} {selectedPatient.last_name}</h2>
                    <p className="text-xs sm:text-sm text-muted-foreground truncate">{selectedPatient.nupn || selectedPatient.id?.slice(0, 8)}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-1 sm:gap-2 text-xs sm:text-sm">
                  <div><span className="text-muted-foreground">Age:</span> {selectedPatient.date_of_birth ? calculateAge(selectedPatient.date_of_birth) : '-'} yrs</div>
                  <div className="capitalize"><span className="text-muted-foreground">Gender:</span> {selectedPatient.gender}</div>
                  <div className="col-span-2"><span className="text-muted-foreground">DOB:</span> {selectedPatient.date_of_birth || '-'}</div>
                  <div className="col-span-2 truncate"><span className="text-muted-foreground">Phone:</span> {selectedPatient.phone || '-'}</div>
                  <div className="col-span-2 truncate"><span className="text-muted-foreground">Address:</span> {[selectedPatient.address_line, selectedPatient.city, selectedPatient.district].filter(Boolean).join(', ') || '-'}</div>
                </div>
                {selectedPatient.allergies && selectedPatient.allergies.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Allergies</p>
                    <div className="flex gap-1 flex-wrap">
                      {selectedPatient.allergies.map((a, i) => <Badge key={i} variant="critical" className="text-xs">{a.allergen}</Badge>)}
                    </div>
                  </div>
                )}
                <Button size="sm" className="w-full" asChild><Link href={`/emr/edit-patient?id=${selectedPatient.id}`}>Edit Patient Info</Link></Button>
              </CardContent>
            </Card>

            <div className="hidden sm:block">
              <VoiceRecorder onTranscriptionComplete={() => {}} />
            </div>
          </div>

          <div className="lg:col-span-2 space-y-4 sm:space-y-6">
            <Tabs defaultValue="encounters">
              <TabsList className="flex-wrap">
                <TabsTrigger value="encounters" className="text-xs sm:text-sm"><ClipboardList className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Encounters</TabsTrigger>
                <TabsTrigger value="labs" className="text-xs sm:text-sm"><Activity className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Lab Results</TabsTrigger>
                <TabsTrigger value="soap" className="text-xs sm:text-sm"><FileText className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />SOAP Notes</TabsTrigger>
                <TabsTrigger value="meds" className="text-xs sm:text-sm"><Heart className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Medications</TabsTrigger>
              </TabsList>

              <TabsContent value="encounters">
                <Card>
                  <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Patient Encounters</CardTitle></CardHeader>
                  <CardContent className="p-3 sm:p-4">
                    {encounters.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-6">No encounters recorded</p>
                    ) : (
                      <div className="space-y-2 sm:space-y-3">
                        {encounters.map((enc) => (
                          <div key={enc.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 rounded-lg border hover:bg-accent/50 gap-2">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-medium text-sm">{enc.encounter_type?.replace('_', ' ')}</span>
                                <Badge variant="outline" className="text-xs">{enc.encounter_datetime ? formatDate(enc.encounter_datetime) : '-'}</Badge>
                                <Badge variant={enc.status === 'completed' ? 'success' : 'outline'} className="text-xs">{enc.status}</Badge>
                              </div>
                              <p className="text-xs sm:text-sm text-muted-foreground mt-1 truncate">{enc.chief_complaint || enc.diagnosis || '-'}</p>
                              {enc.provider_name && <p className="text-xs text-muted-foreground">{enc.provider_name}</p>}
                            </div>
                            <Button variant="ghost" size="sm" className="self-end sm:self-center" onClick={() => router.push(`/clinical-notes?encounter=${enc.id}`)}>View</Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="labs">
                <Card>
                  <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Lab Results</CardTitle></CardHeader>
                  <CardContent className="p-3 sm:p-4">
                    {labs.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-6">No lab results</p>
                    ) : (
                      <div className="space-y-2 sm:space-y-3">
                        {labs.map((lab) => (
                          <div key={lab.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 rounded-lg border gap-2">
                            <div className="min-w-0">
                              <p className="font-medium text-sm truncate">{lab.order_description}</p>
                              <p className="text-xs text-muted-foreground">{lab.performed_datetime ? formatDate(lab.performed_datetime) : '-'}</p>
                            </div>
                            <div className="text-left sm:text-right shrink-0">
                              <p className="font-bold text-sm">{lab.result_value || 'Pending'}</p>
                              {lab.result_unit && <span className="text-xs text-muted-foreground ml-1">{lab.result_unit}</span>}
                              {lab.interpretation && (
                                <Badge variant={lab.interpretation === 'normal' ? 'success' : lab.interpretation === 'abnormal' ? 'warning' : 'destructive'} className="text-xs ml-2">
                                  {lab.interpretation}
                                </Badge>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="soap">
                <SoapNoteEditor
                  encounterId="new"
                  initialNote={{ subjective: '', objective: '', assessment: '', plan: '' }}
                  onSave={() => {}}
                />
              </TabsContent>

              <TabsContent value="meds">
                <Card>
                  <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Current Medications</CardTitle></CardHeader>
                  <CardContent className="p-3 sm:p-4">
                    <p className="text-sm text-muted-foreground text-center py-6">Select a patient encounter to view medications</p>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
