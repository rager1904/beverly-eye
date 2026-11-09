'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend } from 'recharts';
import { BarChart3, TrendingUp, Users, Calendar } from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import { useState } from 'react';

const monthlyPatients = [
  { month: 'Jan', patients: 450, encounters: 680 },
  { month: 'Feb', patients: 520, encounters: 750 },
  { month: 'Mar', patients: 580, encounters: 820 },
  { month: 'Apr', patients: 490, encounters: 710 },
  { month: 'May', patients: 610, encounters: 890 },
  { month: 'Jun', patients: 650, encounters: 920 },
];

const diseaseBreakdown = [
  { name: 'Malaria', value: 35, color: '#ef4444' },
  { name: 'Hypertension', value: 25, color: '#f59e0b' },
  { name: 'Diabetes', value: 15, color: '#0ea5e9' },
  { name: 'HIV/AIDS', value: 12, color: '#8b5cf6' },
  { name: 'Cholera', value: 8, color: '#22c55e' },
  { name: 'Other', value: 5, color: '#64748b' },
];

const ageDistribution = [
  { age: '0-5', male: 120, female: 115 },
  { age: '6-17', male: 180, female: 175 },
  { age: '18-35', male: 320, female: 350 },
  { age: '36-50', male: 280, female: 290 },
  { age: '51-65', male: 190, female: 210 },
  { age: '65+', male: 110, female: 130 },
];

const topDiagnoses = [
  { code: 'B54', description: 'Malaria (uncomplicated)', count: 1245, trend: '+12%' },
  { code: 'I10', description: 'Essential hypertension', count: 892, trend: '+5%' },
  { code: 'E11', description: 'Type 2 diabetes mellitus', count: 654, trend: '+8%' },
  { code: 'J15', description: 'Bacterial pneumonia', count: 432, trend: '-3%' },
  { code: 'A09', description: 'Infectious gastroenteritis', count: 398, trend: '+15%' },
];

export default function AnalyticsPage() {
  const [chatOpen, setChatOpen] = useState(false);
  const [period, setPeriod] = useState('6m');

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-healthcare-blue" />
            Analytics Dashboard
          </h1>
          <p className="text-muted-foreground">Population health insights and operational metrics</p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Period" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="1m">Last Month</SelectItem>
            <SelectItem value="3m">Last 3 Months</SelectItem>
            <SelectItem value="6m">Last 6 Months</SelectItem>
            <SelectItem value="1y">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Total Patients', value: '3,850', change: '+12.5%', icon: Users },
          { label: 'Monthly Encounters', value: '4,770', change: '+8.3%', icon: Calendar },
          { label: 'Active Diseases', value: '24', change: '-2', icon: TrendingUp },
          { label: 'Facility Occupancy', value: '82.4%', change: '+3.1%', icon: BarChart3 },
        ].map(({ label, value, change, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <Icon className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
                <span className={`text-xs ${change.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>{change}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-lg">Patient Volume & Encounters</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyPatients}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="patients" stroke="#22c55e" strokeWidth={2} name="Patients" />
                <Line type="monotone" dataKey="encounters" stroke="#0ea5e9" strokeWidth={2} name="Encounters" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Disease Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={diseaseBreakdown} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={3} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {diseaseBreakdown.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Age & Gender Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={ageDistribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="age" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="male" fill="#0ea5e9" name="Male" />
                <Bar dataKey="female" fill="#f472b6" name="Female" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Top Diagnoses (ICD-10)</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topDiagnoses.map((dx, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-600">{i + 1}</span>
                    <div>
                      <p className="font-medium text-sm">{dx.code} - {dx.description}</p>
                      <p className="text-xs text-muted-foreground">{dx.count} cases</p>
                    </div>
                  </div>
                  <span className={`text-sm font-medium ${dx.trend.startsWith('+') ? 'text-red-500' : 'text-green-500'}`}>{dx.trend}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
