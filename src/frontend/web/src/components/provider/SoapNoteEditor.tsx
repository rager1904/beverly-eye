'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles, Save, Mic, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '@/lib/auth';

interface SoapNoteEditorProps {
  encounterId: string;
  initialNote?: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
  onSave: (note: { subjective: string; objective: string; assessment: string; plan: string }) => void;
}

export function SoapNoteEditor({ encounterId, initialNote, onSave }: SoapNoteEditorProps) {
  const [subjective, setSubjective] = useState(initialNote?.subjective || '');
  const [objective, setObjective] = useState(initialNote?.objective || '');
  const [assessment, setAssessment] = useState(initialNote?.assessment || '');
  const [plan, setPlan] = useState(initialNote?.plan || '');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const user = useAuthStore((s) => s.user);

  const handleSave = () => onSave({ subjective, objective, assessment, plan });

  const handleAiAssist = async () => {
    if (!subjective && !objective) {
      toast.error('Add subjective and objective first');
      return;
    }
    setAiLoading(true);
    try {
      const response = await fetch('/api/v1/agents/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${useAuthStore.getState().accessToken}`,
        },
        body: JSON.stringify({
          message: `Generate a SOAP assessment and plan based on:\n\nSubjective: ${subjective}\n\nObjective: ${objective}\n\nAssessment so far: ${assessment}\n\nCurrent plan: ${plan}`,
          conversation_id: `soap-${encounterId}-${Date.now()}`,
          agent: 'clinical_documentation',
          metadata: { action: 'soap_suggest', transcript: `Subjective: ${subjective}\nObjective: ${objective}\nAssessment: ${assessment}\nPlan: ${plan}`, encounter_id: encounterId, specialty: user?.specialty },
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setAiSuggestion(data.response || data.message || '');
      } else {
        const err = await response.json().catch(() => ({ detail: 'AI assist failed' }));
        toast.error(err.detail || 'AI assist failed');
      }
    } catch {
      toast.error('AI assist unavailable');
    }
    setAiLoading(false);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-healthcare-blue" />
          SOAP Note
        </CardTitle>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleAiAssist} disabled={aiLoading}>
            <Sparkles className={`h-4 w-4 mr-1 ${aiLoading ? 'animate-spin' : ''}`} />
            AI Assist
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="h-4 w-4 mr-1" />Save
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="edit">
          <TabsList className="mb-4">
            <TabsTrigger value="edit">Edit</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
            {aiSuggestion && <TabsTrigger value="ai-suggest">AI Suggestion <Badge variant="info" className="ml-1 text-xs">New</Badge></TabsTrigger>}
          </TabsList>

          <TabsContent value="edit" className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Subjective</label>
              <Textarea
                placeholder="Patient's chief complaint, history of present illness..."
                value={subjective}
                onChange={(e) => setSubjective(e.target.value)}
                rows={3}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Objective</label>
              <Textarea
                placeholder="Vital signs, physical exam findings, lab results..."
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                rows={3}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Assessment</label>
              <Textarea
                placeholder="Diagnosis, differential, severity..."
                value={assessment}
                onChange={(e) => setAssessment(e.target.value)}
                rows={3}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Plan</label>
              <Textarea
                placeholder="Medications, follow-up, referrals, patient education..."
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                rows={3}
              />
            </div>
          </TabsContent>

          <TabsContent value="preview" className="space-y-4 prose prose-sm max-w-none">
            <div>
              <h4 className="text-sm font-semibold text-muted-foreground">S:</h4>
              <p>{subjective || 'No data entered'}</p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-muted-foreground">O:</h4>
              <p>{objective || 'No data entered'}</p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-muted-foreground">A:</h4>
              <p>{assessment || 'No data entered'}</p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-muted-foreground">P:</h4>
              <p>{plan || 'No data entered'}</p>
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
                  <Button size="sm" variant="outline" onClick={() => { setAssessment(aiSuggestion); setAiSuggestion(''); }}>
                    Apply to Assessment
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setAiSuggestion('')}>Dismiss</Button>
                </div>
              </div>
            </TabsContent>
          )}
        </Tabs>
      </CardContent>
    </Card>
  );
}
