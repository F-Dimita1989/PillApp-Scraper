/**
 * Se il backend su Render è Node.js (Express), aggiungi questa route
 * che fa proxy verso il modulo Python su un secondo servizio Render,
 * OPPURE integra drug_image_fetcher nel servizio Python principale.
 *
 * Opzione A (consigliata): backend Python su Render → usa drug_image_fetcher/routes.py
 * Opzione B: due servizi Render → Node proxy verso servizio Python
 */

const express = require('express');

const router = express.Router();

// URL del servizio Python su Render (solo se usi 2 servizi separati)
const DRUG_IMAGE_SERVICE_URL =
  process.env.DRUG_IMAGE_SERVICE_URL || 'https://pillapp-drug-image.onrender.com';

router.post('/api/v1/drugs/image', async (req, res) => {
  try {
    const response = await fetch(`${DRUG_IMAGE_SERVICE_URL}/api/v1/drugs/image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(25_000),
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (error) {
    return res.status(503).json({
      success: false,
      imageUrl: null,
      message: 'Servizio immagini temporaneamente non disponibile',
      rejectedReasons: [],
      matchedFields: [],
      confidenceScore: 0,
    });
  }
});

module.exports = router;

// Nel tuo app.js:
// const drugImageRoutes = require('./routes/drugImage');
// app.use(drugImageRoutes);
