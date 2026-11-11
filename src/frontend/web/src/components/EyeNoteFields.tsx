import { useId } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export type EyeDetails = Record<string, string>;

const sections = [
  { title: 'Patient details', fields: [
    ['name', 'Name'], ['medical_aid', 'Medical aid'], ['address', 'Address'],
    ['number', 'Number'], ['referred_by', 'Referred by'], ['member', 'Member'],
    ['allergies', 'Allergies'], ['suffix', 'Suffix'], ['next_of_kin', 'Next of kin'],
    ['date_of_birth', 'Date of birth'], ['telephone', 'Telephone'], ['employer', 'Employer'],
  ] },
  { title: 'A. History', fields: [
    ['problem', 'Problem'], ['past_ocular_history', 'Past ocular history'],
    ['health', 'Health'], ['medication', 'Medication'], ['family_history', 'Family history'],
    ['social_history', 'Social history'],
  ] },
  { title: 'B. Examination', fields: [
    ['vision_without_glasses', 'Vision without glasses'], ['ocular_motility', 'Ocular motility'],
    ['vision_with_glasses', 'Vision with glasses'], ['vision_pinhole', 'Vision pinhole'],
    ['refraction', 'Refraction'], ['iop', 'IOP'], ['anterior_segments', 'Anterior segments'],
    ['pupils', 'Pupils'], ['fundi', 'Fundi'],
  ] },
  { title: 'C. Diagnosis', fields: [
    ['diagnosis', 'Diagnosis'], ['k1', 'Biometry K1'], ['k2', 'Biometry K2'], ['iol', 'IOL'],
    ['power', 'Power'], ['final_refraction', 'Final refraction'],
  ] },
] as const;

export function EyeNoteFields({ values, onChange }: {
  values: EyeDetails;
  onChange?: (key: string, value: string) => void;
}) {
  const prefix = useId();
  return (
    <div className="space-y-5">
      {sections.map(({ title, fields }, index) => (
        <fieldset key={title} className="min-w-0 rounded-lg border p-3 sm:p-4">
          <legend className="px-1 text-sm font-semibold">{title}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map(([key, label]) => {
              const id = `${prefix}-${key}`;
              const value = values[key] ?? '';
              return (
                <div key={key} className="min-w-0 space-y-1">
                  {onChange ? (
                    <>
                      <label htmlFor={id} className="text-sm font-medium">{label}</label>
                      {index === 0 && key !== 'allergies' ? (
                        <Input id={id} value={value} maxLength={8000}
                          type={key === 'date_of_birth' ? 'date' : key === 'telephone' ? 'tel' : 'text'}
                          onChange={(event) => onChange(key, event.target.value)} />
                      ) : (
                        <Textarea id={id} value={value} rows={2} maxLength={8000}
                          onChange={(event) => onChange(key, event.target.value)} />
                      )}
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-medium">{label}</p>
                      <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{value || '—'}</p>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
