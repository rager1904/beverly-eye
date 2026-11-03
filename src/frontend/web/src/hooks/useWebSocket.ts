'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Client, IMessage, StompSubscription } from '@stomp/stompjs';
import { useAuthStore } from '@/lib/auth';
import type { WebSocketMessage } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

type MessageHandler = (message: WebSocketMessage) => void;

const handlers = new Map<string, Set<MessageHandler>>();

export function useWebSocket() {
  const clientRef = useRef<Client | null>(null);
  const subscriptionsRef = useRef<Map<string, StompSubscription>>(new Map());
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);

  const connect = useCallback(() => {
    if (!accessToken || clientRef.current?.active) return;

    const client = new Client({
      brokerURL: WS_URL,
      connectHeaders: { Authorization: `Bearer ${accessToken}` },
      reconnectDelay: 5000,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,
      onConnect: () => {
        const sub = client.subscribe('/topic/notifications', (message: IMessage) => {
          try {
            const parsed: WebSocketMessage = JSON.parse(message.body);
            const topicHandlers = handlers.get(parsed.type);
            if (topicHandlers) topicHandlers.forEach((h) => h(parsed));
            invalidateQueriesForType(parsed.type);
          } catch { /* ignore malformed */ }
        });
        subscriptionsRef.current.set('notifications', sub);
      },
      onDisconnect: () => { subscriptionsRef.current.clear(); },
      onStompError: (frame) => { console.error('STOMP error:', frame.headers['message']); },
    });

    client.activate();
    clientRef.current = client;
  }, [accessToken]);

  const disconnect = useCallback(() => {
    subscriptionsRef.current.forEach((sub) => sub.unsubscribe());
    subscriptionsRef.current.clear();
    clientRef.current?.deactivate();
    clientRef.current = null;
  }, []);

  const subscribe = useCallback((topic: string, handler: MessageHandler) => {
    if (!handlers.has(topic)) handlers.set(topic, new Set());
    handlers.get(topic)!.add(handler);
    return () => { handlers.get(topic)?.delete(handler); };
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { subscribe, disconnect, reconnect: connect };
}

function invalidateQueriesForType(type: string) {
  const queryClient = useQueryClient();
  const queryMap: Record<string, string[]> = {
    appointment_created: ['appointments'],
    appointment_updated: ['appointments'],
    vital_signs_recorded: ['patient-vitals'],
    lab_result_updated: ['patient-labs'],
    lab_result_critical: ['patient-labs', 'lab-results'],
    telemedicine_started: ['telemedicine-sessions'],
    telemedicine_ended: ['telemedicine-sessions'],
    disease_alert: ['disease-alerts'],
    bed_occupancy_changed: ['bed-occupancy'],
    pharmacy_stock_low: ['pharmacy-stock'],
    queue_updated: ['patient-queue'],
  };
  const keys = queryMap[type];
  if (keys) keys.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
}
