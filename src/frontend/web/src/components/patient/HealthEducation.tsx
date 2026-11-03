'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Play, Download, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { HealthEducationResource } from '@/types';

interface HealthEducationProps {
  resources: HealthEducationResource[];
  isLoading?: boolean;
}

const categoryIcons: Record<string, string> = {
  maternal: '🤰',
  child: '👶',
  malaria: '🦟',
  hiv: '❤️',
  nutrition: '🥗',
  hygiene: '🧼',
  diabetes: '🩸',
  hypertension: '💓',
  mental: '🧠',
  covid: '🦠',
};

export function HealthEducation({ resources, isLoading }: HealthEducationProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><BookOpen className="h-5 w-5" />Health Education</CardTitle></CardHeader>
        <CardContent><div className="grid gap-3 sm:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => (<div key={i} className="h-28 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <BookOpen className="h-5 w-5 text-healthcare-blue" />
          Health Education
        </CardTitle>
      </CardHeader>
      <CardContent>
        {resources.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No resources available</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {resources.map((resource) => (
              <div key={resource.id} className="p-4 rounded-lg border bg-card hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{categoryIcons[resource.category] || '📋'}</span>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-sm leading-tight">{resource.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{resource.description}</p>
                    <div className="flex items-center gap-2 mt-2">
                      {resource.language !== 'en' && (
                        <Badge variant="secondary" className="text-xs flex items-center gap-1">
                          <Globe className="h-3 w-3" />{resource.language.toUpperCase()}
                        </Badge>
                      )}
                      {resource.is_offline_available && (
                        <Badge variant="outline" className="text-xs">Offline</Badge>
                      )}
                    </div>
                    <div className="flex gap-2 mt-2">
                      {resource.video_url && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs">
                          <Play className="h-3 w-3 mr-1" />Watch
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" className="h-7 text-xs">
                        <Download className="h-3 w-3 mr-1" />Save
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
