'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { type AgentState, useVoiceAssistant } from '@livekit/components-react';
import type { Expression } from '@/components/robot/robo-face/expressions';

type RobotExpressionContextValue = {
  expression: Expression;
  baseExpression: Expression;
  overrideExpression: Expression | null;
  triggerExpression: (expr: Expression, durationMs?: number) => void;
  clearOverride: () => void;
};

const RobotExpressionContext = createContext<RobotExpressionContextValue | null>(null);

function mapAgentStateToExpression(state: AgentState): Expression {
  switch (state) {
    case 'connecting':
      return 'processing';
    case 'listening':
      return 'listening';
    case 'thinking':
      return 'thinking';
    case 'speaking':
      return 'neutral';
    default:
      return 'neutral';
  }
}

export function RobotExpressionProvider({ children }: { children: React.ReactNode }) {
  const { state } = useVoiceAssistant();
  const baseExpression = useMemo(() => mapAgentStateToExpression(state), [state]);

  const [override, setOverride] = useState<{ expr: Expression; until: number } | null>(null);
  const timerRef = useRef<number | null>(null);

  const clearOverride = useCallback(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = null;
    setOverride(null);
  }, []);

  const triggerExpression = useCallback((expr: Expression, durationMs: number = 3000) => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    const until = Date.now() + Math.max(0, durationMs);
    setOverride({ expr, until });
    timerRef.current = window.setTimeout(() => {
      setOverride((curr) => (curr && Date.now() >= curr.until ? null : curr));
      timerRef.current = null;
    }, durationMs + 50) as unknown as number;
  }, []);

  useEffect(() => {
    if (override && Date.now() >= override.until) {
      setOverride(null);
    }
  }, [override]);

  useEffect(() => () => clearOverride(), [clearOverride]);

  const effective: Expression = override ? override.expr : baseExpression;

  const value = useMemo<RobotExpressionContextValue>(
    () => ({
      expression: effective,
      baseExpression,
      overrideExpression: override?.expr ?? null,
      triggerExpression,
      clearOverride,
    }),
    [effective, baseExpression, override?.expr, triggerExpression, clearOverride]
  );

  return (
    <RobotExpressionContext.Provider value={value}>{children}</RobotExpressionContext.Provider>
  );
}

export function useRobotExpression() {
  const ctx = useContext(RobotExpressionContext);
  if (!ctx) throw new Error('useRobotExpression must be used within RobotExpressionProvider');
  return ctx;
}
