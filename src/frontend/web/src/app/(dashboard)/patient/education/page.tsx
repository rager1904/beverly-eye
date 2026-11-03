'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Download, Globe, Search, ArrowLeft, FileText, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface Resource {
  id: string;
  title: string;
  description: string;
  category: string;
  language: string;
  is_offline_available: boolean;
  target_audience: string[];
}

const categories = ['all', 'maternal', 'child', 'malaria', 'hiv', 'nutrition', 'hygiene', 'diabetes', 'hypertension', 'mental'];

const categoryIcons: Record<string, string> = {
  maternal: '\u{1F930}', child: '\u{1F476}', malaria: '\u{1F99F}', hiv: '\u2764\uFE0F',
  nutrition: '\u{1F957}', hygiene: '\u{1F9FC}', diabetes: '\u{1FA78}', hypertension: '\u{1F493}', mental: '\u{1F9E0}',
};

export default function HealthEducationPage() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.accessToken);

  const fetchResources = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/emr/patients?limit=1', {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchResources(); }, [fetchResources]);

  // No dedicated health education endpoint available yet, show empty state
  const filtered = resources.filter((r) => {
    if (activeCategory !== 'all' && r.category !== activeCategory) return false;
    if (search && !r.title.toLowerCase().includes(search.toLowerCase()) && !r.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/patient"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-healthcare-green" />
            Health Education
          </h1>
          <p className="text-muted-foreground">Learn about managing your health and preventing disease.</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search resources..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex gap-2 flex-wrap">
          {categories.map((cat) => (
            <Button key={cat} variant={activeCategory === cat ? 'default' : 'outline'} size="sm" onClick={() => setActiveCategory(cat)} className="capitalize">
              {cat === 'all' ? null : <span className="mr-1">{categoryIcons[cat]}</span>}{cat}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No resources available yet. Health education content coming soon.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((resource) => (
            <Card key={resource.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{categoryIcons[resource.category] || '\u{1F4CB}'}</span>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm leading-tight">{resource.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{resource.description}</p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {resource.language !== 'en' && (
                        <Badge variant="secondary" className="text-xs"><Globe className="h-3 w-3 mr-1" />{resource.language.toUpperCase()}</Badge>
                      )}
                      {resource.is_offline_available && <Badge variant="outline" className="text-xs">Offline</Badge>}
                      {resource.target_audience.map((a) => (
                        <Badge key={a} variant="outline" className="text-xs bg-blue-50">{a}</Badge>
                      ))}
                    </div>
                    <div className="flex gap-2 mt-3">
                      <Button variant="default" size="sm" className="h-8 text-xs">View Details</Button>
                      {resource.is_offline_available && (
                        <Button variant="ghost" size="sm" className="h-8 text-xs"><Download className="h-3 w-3 mr-1" />Save</Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
