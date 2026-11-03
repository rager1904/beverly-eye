'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot, Stethoscope, Shield, Microscope, Pill, BarChart3, Heart, User } from 'lucide-react';

const roles = [
  { role: 'patient', label: 'Patient', icon: <User className="h-8 w-8" />, desc: 'Your personal health assistant' },
  { role: 'provider', label: 'Healthcare Provider', icon: <Stethoscope className="h-8 w-8" />, desc: 'Clinical decision support' },
  { role: 'nurse', label: 'Nurse', icon: <Heart className="h-8 w-8" />, desc: 'Nursing workflow assistant' },
  { role: 'admin', label: 'Hospital Admin', icon: <Shield className="h-8 w-8" />, desc: 'Administrative intelligence' },
  { role: 'lab-tech', label: 'Lab Technician', icon: <Microscope className="h-8 w-8" />, desc: 'Lab workflow assistant' },
  { role: 'pharmacist', label: 'Pharmacist', icon: <Pill className="h-8 w-8" />, desc: 'Pharmaceutical intelligence' },
  { role: 'public-health', label: 'Public Health Officer', icon: <BarChart3 className="h-8 w-8" />, desc: 'Epidemiological intelligence' },
];

export default function AiGuidePage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Bot className="h-8 w-8 text-healthcare-green" />
          UbuntuCare AI Assistant Guide
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Select your role to see how the AI assistant can help you. Each role has tailored capabilities for your workflow.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {roles.map((r) => (
          <Link key={r.role} href={`/ai-guide/${r.role}`}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="text-healthcare-green">{r.icon}</div>
                  <div>
                    <CardTitle className="text-lg">{r.label}</CardTitle>
                    <CardDescription>{r.desc}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Click to see AI capabilities for {r.label}s</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
