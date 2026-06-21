/**
 * Flusso post-scansione barcode — esempio schermata PillApp.
 * Copia in: src/screens/ScanResultScreen.tsx (adattato al tuo navigator)
 */

import React, { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DrugPackageImage } from './DrugPackageImage';
import type { DrugInfoPayload } from './types';

// Dati che ottieni dal tuo DB/API dopo la scansione AIC
interface ScannedDrug {
  aic: string;
  name: string;
  dosage?: string;
  pharmaceuticalForm?: string;
  packageQuantity?: string;
  marketingAuthorizationHolder?: string;
}

interface ScanResultScreenProps {
  scannedDrug: ScannedDrug;
}

export function ScanResultScreen({ scannedDrug }: ScanResultScreenProps) {
  const drugPayload: DrugInfoPayload = useMemo(
    () => ({
      aic: scannedDrug.aic,
      name: scannedDrug.name,
      dosage: scannedDrug.dosage,
      pharmaceutical_form: scannedDrug.pharmaceuticalForm,
      package_quantity: scannedDrug.packageQuantity,
      marketing_authorization_holder: scannedDrug.marketingAuthorizationHolder,
    }),
    [scannedDrug],
  );

  return (
    <View style={styles.container}>
      <DrugPackageImage drug={drugPayload} size={160} />

      <Text style={styles.name}>{scannedDrug.name}</Text>
      <Text style={styles.meta}>
        AIC {scannedDrug.aic}
        {scannedDrug.dosage ? ` · ${scannedDrug.dosage}` : ''}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    alignItems: 'center',
    gap: 12,
  },
  name: {
    fontSize: 22,
    fontWeight: '600',
  },
  meta: {
    fontSize: 14,
    color: '#52525b',
  },
});
