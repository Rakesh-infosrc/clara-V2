#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const manifestPath = join(process.cwd(), '.next', 'routes-manifest.json');

if (!existsSync(manifestPath)) {
  process.exit(0);
}

try {
  const manifestRaw = readFileSync(manifestPath, 'utf8');
  const manifest = JSON.parse(manifestRaw);

  const needsDataRoutesNormalization = !Array.isArray(manifest.dataRoutes);
  const needsDynamicRoutesNormalization = !Array.isArray(manifest.dynamicRoutes);

  if (needsDataRoutesNormalization) {
    manifest.dataRoutes = [];
  }

  if (needsDynamicRoutesNormalization) {
    manifest.dynamicRoutes = [];
  }

  if (needsDataRoutesNormalization || needsDynamicRoutesNormalization) {
    writeFileSync(manifestPath, JSON.stringify(manifest));
  }
} catch (error) {
  console.error('[ensure-routes-manifest] Failed to normalize manifest:', error);
  process.exit(1);
}
