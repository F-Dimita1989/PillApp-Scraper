/**
 * Hook + componente esempio per PillApp.
 * Copia e adatta in src/components/DrugPackageImage.tsx
 */

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { fetchDrugPackageImage } from './drugImageApi';
import type { DrugImageState, DrugInfoPayload } from './types';

// Sostituisci con un'immagine placeholder nel tuo progetto (es. require('@/assets/drug-placeholder.png'))
const PLACEHOLDER = { uri: 'https://via.placeholder.com/120?text=Farmaco' };

interface DrugPackageImageProps {
  drug: DrugInfoPayload;
  size?: number;
  showConfidence?: boolean;
}

export function DrugPackageImage({
  drug,
  size = 120,
  showConfidence = false,
}: DrugPackageImageProps) {
  const [state, setState] = useState<DrugImageState>({ status: 'idle' });

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setState({ status: 'loading' });
      try {
        const data = await fetchDrugPackageImage(drug, {
          signal: controller.signal,
        });

        if (data.success && data.imageUrl) {
          setState({ status: 'success', data });
        } else {
          // Importante: non mostrare imageUrl se success === false
          setState({ status: 'unavailable', data });
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        const message =
          error instanceof Error ? error.message : 'Errore sconosciuto';
        setState({ status: 'error', error: message });
      }
    }

    load();
    return () => controller.abort();
  }, [
    drug.aic,
    drug.name,
    drug.dosage,
    drug.pharmaceutical_form,
    drug.package_quantity,
    drug.marketing_authorization_holder,
  ]);

  if (state.status === 'loading' || state.status === 'idle') {
    return (
      <View style={[styles.box, { width: size, height: size }]}>
        <ActivityIndicator accessibilityLabel="Caricamento immagine farmaco" />
      </View>
    );
  }

  if (state.status === 'error' || state.status === 'unavailable') {
    return (
      <View style={[styles.box, { width: size, height: size }]}>
        <Image
          source={PLACEHOLDER}
          style={{ width: size, height: size }}
          resizeMode="contain"
          accessibilityLabel="Immagine confezione non disponibile"
        />
        {__DEV__ && state.status === 'unavailable' && (
          <Text style={styles.hint} numberOfLines={2}>
            {state.data.message}
          </Text>
        )}
      </View>
    );
  }

  return (
    <View>
      <Image
        source={{ uri: state.data.imageUrl! }}
        style={{ width: size, height: size }}
        resizeMode="contain"
        accessibilityLabel={`Confezione ${drug.name}`}
      />
      {showConfidence && (
        <Text style={styles.confidence}>
          {(state.data.confidenceScore * 100).toFixed(0)}% affidabile
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f4f4f5',
    borderRadius: 8,
  },
  hint: {
    fontSize: 10,
    color: '#71717a',
    marginTop: 4,
    textAlign: 'center',
  },
  confidence: {
    fontSize: 11,
    color: '#16a34a',
    marginTop: 4,
    textAlign: 'center',
  },
});
