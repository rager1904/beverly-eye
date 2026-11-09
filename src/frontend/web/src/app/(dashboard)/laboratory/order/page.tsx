'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { FlaskConical, ArrowLeft, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { PatientPicker } from '@/components/PatientPicker';
import { clinicalApi } from '@/lib/clinical-api';

const testOptions = [
  { category: 'Parasitology', tests: ['Malaria RDT', 'Malaria Blood Smear', 'Stool O&P', 'Schistosomiasis'] },
  { category: 'Hematology', tests: ['Full Blood Count', 'Hb Electrophoresis', 'Coagulation Profile', 'Blood Grouping'] },
  { category: 'Biochemistry', tests: ['Blood Glucose', 'HbA1c', 'Liver Function Test', 'Renal Function Test', 'Lipid Profile', 'Uric Acid'] },
  { category: 'Microbiology', tests: ['TB GeneXpert', 'Urine Culture', 'Blood Culture', 'Widal Test', 'VDRL/RPR'] },
  { category: 'Serology', tests: ['HIV RDT', 'Hepatitis B Surface Antigen', 'Hepatitis C Antibody', 'Syphilis RDT'] },
  { category: 'Urinalysis', tests: ['Urinalysis Dipstick', 'Urine Microscopy', 'Urine Pregnancy Test'] },
];

export default function OrderLabTestPage() {
  const router = useRouter();
  const role = useAuthStore(s => s.user?.role);
  const [patientId, setPatientId] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTest, setSelectedTest] = useState('');
  const [priority, setPriority] = useState('routine');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId || !selectedTest) {
      toast.error('Please select a registered patient and test');
      return;
    }
    setSubmitting(true);
    try {
      await clinicalApi('emr/orders', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          order_code: selectedTest.toUpperCase().replace(/[^A-Z0-9]+/g, '_').slice(0, 50),
          order_description: selectedTest,
          order_type: 'lab',
          priority,
          clinical_notes: notes || undefined,
        }),
      });
        toast.success('Lab test ordered successfully');
        router.push('/laboratory');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to request test');
    } finally {
      setSubmitting(false);
    }
  };

  const currentCategory = testOptions.find((c) => c.category === selectedCategory);

  if (role !== 'provider' && role !== 'admin') return <p role="alert">Only doctors and administrators can request laboratory tests.</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/laboratory"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <FlaskConical className="h-6 w-6 text-healthcare-blue" />
            Order Lab Test
          </h1>
          <p className="text-muted-foreground">Request a new laboratory test for a patient</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader><CardTitle className="text-lg">Patient Information</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <PatientPicker value={patientId} onChange={setPatientId} />
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Priority *</label>
                  <div className="flex gap-2">
                    {['routine', 'urgent', 'stat'].map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPriority(p)}
                        className={`flex-1 p-2 rounded-lg border text-sm font-medium capitalize transition-colors ${priority === p ? (p === 'stat' ? 'bg-red-50 border-red-300 text-red-600' : p === 'urgent' ? 'bg-amber-50 border-amber-300 text-amber-600' : 'bg-green-50 border-green-300 text-green-600') : 'bg-background hover:bg-accent'}`}
                      >
                        {p === 'stat' && <AlertTriangle className="h-3 w-3 inline mr-1" />}
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Clinical Notes</label>
                  <Textarea placeholder="Any relevant clinical information..." value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3">
            <Card>
              <CardHeader><CardTitle className="text-lg">Select Test</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Test Category</label>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {testOptions.map((cat) => (
                      <button
                        key={cat.category}
                        type="button"
                        onClick={() => { setSelectedCategory(cat.category); setSelectedTest(''); }}
                        className={`p-2 rounded-lg border text-xs font-medium transition-colors ${selectedCategory === cat.category ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                      >
                        {cat.category}
                      </button>
                    ))}
                  </div>
                </div>

                {currentCategory && (
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">Available Tests</label>
                    <div className="grid grid-cols-2 gap-2">
                      {currentCategory.tests.map((test) => (
                        <button
                          key={test}
                          type="button"
                          onClick={() => setSelectedTest(test)}
                          className={`p-3 rounded-lg border text-sm font-medium transition-colors text-left ${selectedTest === test ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                        >
                          {test}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {!selectedCategory && (
                  <p className="text-sm text-muted-foreground text-center py-8">Select a test category above to see available tests</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting}>
            {submitting ? 'Ordering...' : 'Order Test'}
          </Button>
          <Button variant="outline" type="button" asChild>
            <Link href="/laboratory">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
