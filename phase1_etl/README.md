# Phase 1 — ETL vectoriel et validation avec dataset fictif

## Objectif
Valider la logique de base de la phase 1 avec les PDF réels déjà placés dans `data/raw`.

## Étapes
1. Démarrer Qdrant localement.
2. Exécuter `python phase1_etl/01_fake_ingest.py` pour extraire les PDF, créer les chunks et charger Qdrant.
3. Exécuter `python phase1_etl/02_phase1_validation.py` pour vérifier que la recherche sémantique fonctionne avec métadonnées.

## Ce que vous devez vérifier
- la collection contient bien des chunks issus des rapports PDF,
- les résultats retournés correspondent à la requête et au filtre metadata,
- chaque chunk garde les métadonnées utiles : `company`, `year`, `source_file`, `source_page`, `chunk_id`,
- la logique est stable avant de passer à la phase 2.
