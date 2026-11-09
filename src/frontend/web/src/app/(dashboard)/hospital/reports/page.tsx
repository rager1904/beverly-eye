'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Building2, ArrowLeft, FileText, Download, Calendar, BarChart3, TrendingUp, Users, DollarSign } from 'lucide-react';
import Link from 'next/link';
import { formatZMW } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';

const admissionData = [
  { month: 'Jan', admissions: 120, discharges: 105 },
  { month: 'Feb', admissions: 135, discharges: 128 },
  { month: 'Mar', admissions: 150, discharges: 140 },
  { month: 'Apr', admissions: 142, discharges: 138 },
  { month: 'May', admissions: 165, discharges: 155 },
  { month: 'Jun', admissions: 180, discharges: 170 },
];

const departmentRevenue = [
  { department: 'General', revenue: 450000, expenses: 320000 },
  { department: 'Surgery', revenue: 680000, expenses: 420000 },
  { department: 'Maternity', revenue: 320000, expenses: 210000 },
  { department: 'Pharmacy', revenue: 890000, expenses: 540000 },
  { department: 'Lab', revenue: 280000, expenses: 150000 },
];

const diagnosisData = [
  { name: 'Malaria', value: 245, color: '#ef4444' },
  { name: 'Hypertension', value: 180, color: '#f97316' },
  { name: 'Diabetes', value: 120, color: '#eab308' },
  { name: 'Pneumonia', value: 95, color: '#22c55e' },
  { name: 'HIV', value: 80, color: '#0ea5e9' },
  { name: 'Other', value: 210, color: '#a855f7' },
];

const reportTemplates = [
  { name: 'Monthly Admission Summary', description: 'Overview of admissions, discharges, and occupancy rates', icon: Calendar },
  { name: 'Financial Performance Report', description: 'Revenue, expenses, and net income by department', icon: DollarSign },
  { name: 'Clinical Outcomes Report', description: 'Mortality rates, readmission rates, and complication rates', icon: TrendingUp },
  { name: 'Staff Productivity Report', description: 'Consultations, procedures, and patient encounters per provider', icon: Users },
  { name: 'Bed Occupancy Report', description: 'Occupancy trends and capacity planning insights', icon: BarChart3 },
];

export default function ReportsPage() {
  const totalRevenue = departmentRevenue.reduce((s, d) => s + d.revenue, 0);
  const totalExpenses = departmentRevenue.reduce((s, d) => s + d.expenses, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/hospital"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <FileText className="h-6 w-6 text-healthcare-blue" />
            Reports
          </h1>
          <p className="text-muted-foreground">Generate and view hospital reports</p>
        </div>
      </div>

      <Tabs defaultValue="templates">
        <TabsList>
          <TabsTrigger value="templates">Report Templates</TabsTrigger>
          <TabsTrigger value="admissions">Admissions</TabsTrigger>
          <TabsTrigger value="financial">Financial</TabsTrigger>
          <TabsTrigger value="diagnosis">Diagnosis</TabsTrigger>
        </TabsList>

        <TabsContent value="templates">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {reportTemplates.map((template) => (
              <Card key={template.name} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-5">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-healthcare-green/10 flex items-center justify-center flex-shrink-0">
                      <template.icon className="h-5 w-5 text-healthcare-green" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold">{template.name}</h3>
                      <p className="text-xs text-muted-foreground mt-1">{template.description}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button size="sm" variant="outline" className="flex-1"><Download className="h-3 w-3 mr-1" />PDF</Button>
                    <Button size="sm" variant="outline" className="flex-1"><FileText className="h-3 w-3 mr-1" />CSV</Button>
                    <Button size="sm" className="bg-healthcare-green hover:bg-healthcare-green-dark flex-1">Generate</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="admissions">
          <Card>
            <CardHeader><CardTitle className="text-lg">Admission & Discharge Trends</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={admissionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="admissions" stroke="#22c55e" strokeWidth={2} name="Admissions" />
                  <Line type="monotone" dataKey="discharges" stroke="#0ea5e9" strokeWidth={2} name="Discharges" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="financial">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Financial Overview</CardTitle>
              <div className="flex gap-4 mt-2">
                <div className="p-2 rounded-lg bg-green-50 border border-green-200 text-center flex-1">
                  <p className="text-xs text-muted-foreground">Total Revenue</p>
                  <p className="text-lg font-bold text-green-600">{formatZMW(totalRevenue)}</p>
                </div>
                <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-center flex-1">
                  <p className="text-xs text-muted-foreground">Total Expenses</p>
                  <p className="text-lg font-bold text-red-600">{formatZMW(totalExpenses)}</p>
                </div>
                <div className="p-2 rounded-lg bg-blue-50 border border-blue-200 text-center flex-1">
                  <p className="text-xs text-muted-foreground">Net Income</p>
                  <p className="text-lg font-bold text-blue-600">{formatZMW(totalRevenue - totalExpenses)}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={departmentRevenue}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="department" />
                  <YAxis />
                  <Tooltip formatter={(value: number) => formatZMW(value)} />
                  <Bar dataKey="revenue" fill="#22c55e" name="Revenue" />
                  <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="diagnosis">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-lg">Diagnosis Distribution</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={diagnosisData} dataKey="value" cx="50%" cy="50%" outerRadius={100} label={({ name, value }) => `${name}: ${value}`}>
                      {diagnosisData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-lg">Summary</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {diagnosisData.map((d) => (
                    <div key={d.name} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                        <span className="font-medium text-sm">{d.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold">{d.value}</span>
                        <Badge variant="outline">{Math.round(d.value / diagnosisData.reduce((s, x) => s + x.value, 0) * 100)}%</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
