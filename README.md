# MS-Admin

Back-office du catalogue de réseaux de transport. Le service recense les jeux de données GTFS publiés sur transport.data.gouv.fr, conserve ceux que l'exploitant enregistre, et pilote leur agrégation.

| | |
|---|---|
| Langage | Python 3.12+ |
| API | GraphQL fédéré (Apollo Federation 2.0) |
| Port hôte | 8001 (80 dans le conteneur) |
| Base | MongoDB |
| Broker | RabbitMQ |
| Processus | 2 (API + worker) |

## Ce que fait le service

Le service fait deux choses, sur deux objets différents qu'il faut distinguer.

**Il interroge un catalogue externe.** La query `searchTransitNetworksDatasets` appelle l'API de transport.data.gouv.fr en direct, filtre les jeux de données de type `public-transit` et les renvoie normalisés en `StandardDatasets`. Rien n'est stocké : c'est une vue en lecture sur un catalogue tiers d'environ 480 entrées.

**Il tient un registre.** Quand l'administrateur choisit un jeu de données, `createTransitNetwork` l'enregistre en base comme `TransitNetwork` et publie une demande d'ingestion à destination de MS-aom-agregator. Celui-ci télécharge l'archive GTFS, la parse, alimente sa propre base, puis renvoie un accusé qui fait avancer le statut du réseau.

`StandardDatasets` est un catalogue externe volatile, `TransitNetwork` est le registre persistant. Seul le second porte un statut. Les deux partagent la clé `externalId`, ce qui permet de les croiser côté front sans requête supplémentaire.

## Architecture

Le dépôt produit une seule image, lancée deux fois : l'API GraphQL sous uvicorn, et un worker FastStream. **Le worker n'est pas optionnel** : sans lui, aucun statut ne progresse jamais.

```mermaid
flowchart LR
    API["API MS-Admin<br/>uvicorn, port 80"]
    AGG["MS-aom-agregator<br/>télécharge, parse, ingère"]
    WRK["Worker MS-Admin<br/>FastStream"]
    DB[("MongoDB<br/>statut")]

    API -- "gtfs.file.available<br/>network_id, url, format" --> AGG
    AGG -- "gtfs.ingestion.result<br/>network_id, status, error" --> WRK
    WRK --> DB
    DB --> API
    WRK -- "notification_requested<br/>notifications_queue" --> NOTIF["MS-notifications<br/>mail à l'admin"]
```

La boucle de retour est complète : l'agrégateur publie le résultat de chaque ingestion sur `gtfs.ingestion.result`, succès comme échec, et le worker le consomme pour faire avancer le statut. **Ce publisher n'existe toutefois que sur la branche `develop` de MS-aom-agregator, pas encore sur sa `main`.** Un agrégateur déployé depuis `main` ingère les données sans jamais renvoyer d'accusé : les arrêts et les lignes sont bien en base et servis par l'API, mais le réseau reste indéfiniment « en attente d'agrégation » ici, et un échec d'ingestion devient indistinguable d'une ingestion en cours.

La topologie des queues est déclarée dans `app/core/topology.py`, un fichier **dupliqué à l'identique dans les deux dépôts**. Une déclaration AMQP étant idempotente tant que les paramètres concordent, chaque service déclare tout ce qu'il touche et l'ordre de démarrage n'a plus d'importance. En contrepartie, toute divergence entre les deux copies provoque un `PRECONDITION_FAILED` au démarrage : les modifier ensemble est une obligation, pas une préférence.

Le service est un **subgraph Apollo Federation 2.0**. Il n'est normalement pas appelé en direct : le front passe par le router sur le port 4000, qui l'atteint via l'alias réseau `service-admin`. Son type `TransitNetwork` porte `@key(fields: "externalId")`, et MS-aom-agregator s'en sert pour résoudre le réseau d'un arrêt sans dupliquer ses métadonnées.

## Modèle de données

Une seule collection Mongo : `admin_db.registered_transit_network`. Aucun schéma imposé, les documents sont écrits depuis l'input GraphQL. La clé métier est `external_id`, reprise telle quelle du catalogue data.gouv.

Le champ `status` stocke le nom de l'énumération sous forme de chaîne. Les documents antérieurs à son introduction n'ont pas ce champ et retombent sur `PENDING_AGGREGATION` à la lecture : aucune migration n'a été nécessaire, et aucune ne l'est.

| Statut | Libellé | Qui le pose |
|---|---|---|
| `PENDING_AGGREGATION` | En attente d'agrégation | MS-Admin, à la création et à chaque relance |
| `DATA_AVAILABLE` | Données ajoutées | Le worker, sur `status: "ok"` |
| `AGGREGATION_ERROR` | Agrégation en erreur | Le worker, sur `status: "error"` |
| `OUT_OF_SERVICE` | Hors service | À la main, via `updateTransitNetwork` |

**Les libellés français ne sont pas dans l'énumération.** GraphQL ne sérialise jamais que le *nom* d'une valeur d'énumération, pas sa valeur. Le champ calculé `statusLabel` existe pour ça : il renvoie le libellé depuis la table `STATUS_LABELS`, ce qui garde les traductions à un seul endroit au lieu de les redéclarer dans chaque front. Consommer `status` pour la logique, `statusLabel` pour l'affichage.

## Surface GraphQL

| Opération | Rôle | Effet de bord |
|---|---|---|
| `searchTransitNetworksDatasets` | Catalogue data.gouv filtré sur les transports publics | Appel HTTP sortant |
| `getRegistredTransitNetworks` | Registre paginé | — |
| `createTransitNetwork` | Enregistre un réseau | Publie une demande d'ingestion |
| `updateTransitNetwork` | Met à jour un réseau | Réécrit le document entier |
| `retriggerAggregation` | Relance l'ingestion | Publie, puis repasse en attente |
| `deleteTransitNetwork` | Supprime un réseau | — |

**Attention à `updateTransitNetwork`** : elle fait un `$set` du document reconstruit depuis l'input. Tout champ absent de l'input est écrasé. C'est pourquoi le changement de statut passe par `set_status`, qui écrit uniquement le champ concerné, et pourquoi la mutation ignore `status` quand il vaut `null` — sinon un update partiel effacerait l'état d'agrégation.

Dans `retriggerAggregation`, la publication précède délibérément le changement de statut. Le broker est configuré avec `on_return_raises`, donc un message non routable lève une erreur : si la publication échoue, le statut n'est pas touché et l'utilisateur voit l'échec, plutôt qu'un réseau affiché « en attente » d'une ingestion jamais demandée.

## Contrats de message

### Sortant : `gtfs.file.available`

Émis par le **process API** à la création d'un réseau et à chaque relance. Message persistant, queue durable.

```json
{
  "network_id": "63b4c3d2d7857ab0c49dde9a",
  "url": "https://transport.data.gouv.fr/resources/83710/download",
  "format": "GTFS"
}
```

L'URL est celle de la première ressource déclarée au format `GTFS`, à l'exclusion des `gtfs-rt` et des `NeTEx` qu'un même réseau publie souvent. À défaut, on retombe sur l'`endpointUrl` du réseau ; s'il est vide lui aussi, la relance échoue avec un message explicite. Le champ `format` vaut toujours `GTFS` aujourd'hui : il rend le contrat explicite et extensible, il ne varie pas encore.

### Entrant : `gtfs.ingestion.result`

Consommé par le **worker**. Validé par pydantic : `status` n'accepte que `ok` ou `error`, toute autre valeur est rejetée.

```json
{
  "network_id": "63b4c3d2d7857ab0c49dde9a",
  "status": "ok",
  "error": null
}
```

Côté MS-aom-agregator, le publisher est en place dans `app/workers/callbacks/gtfs_callback.py` sur la branche `develop` : le traitement est encadré d'un `try/except` qui publie dans les deux cas, le champ `format` du message entrant est transmis à la `ParserFactory` au lieu du `"GTFS"` codé en dur, et l'exception est relancée après publication (politique `REJECT_ON_ERROR`, donc pas de remise en file). Il est en revanche **absent de la `main` de MS-aom-agregator**. `app/test_ingestion_publisher.py` reste le moyen de tester la boucle sans lancer l'agrégateur.

### Sortant : `notification_requested`

Émis par le **worker** après chaque résultat d'ingestion traité pour un réseau connu, succès comme échec, sur la queue `notifications_queue`. Message persistant, queue durable.

MS-notifications est un service NestJS : son transport RabbitMQ attend l'enveloppe qu'un `ClientProxy.emit()` produirait. MS-Admin étant en Python, `app/workers/publishers/notification_publisher.py` la construit à la main.

`notification_requested` est un contrat générique : MS-notifications ne rédige ni ne décide rien, il persiste puis livre tel quel. **Destinataire, objet et texte du mail sont donc décidés ici**, dans `_rediger_notification` de `app/workers/callbacks/ingestion_callback.py`.

```json
{
  "pattern": "notification_requested",
  "data": {
    "user_id": "admin",
    "recipient_email": "admin@example.com",
    "subject": "Échec d'agrégation — HubertApp",
    "content": "L'agrégation du réseau « Réseau de Paris » a échoué : flux corrompu",
    "type": "AGGREGATION_ERROR",
    "channels": ["EMAIL"],
    "triggered_by": "ms-admin",
    "occurred_at": "2026-09-26T12:00:00+00:00"
  }
}
```

Le destinataire vient de `ADMIN_NOTIFICATION_EMAIL` (variable d'environnement de MS-Admin, lue par `Properties`) ; sans elle, le worker logue `Notification admin ignoree` et ne publie rien. `ADMIN_USER_ID` (défaut `admin`) n'est qu'une clé de persistance côté MS-notifications, elle ne correspond à aucun compte MS-User. `type` (`AGGREGATION_SUCCESS` / `AGGREGATION_ERROR`) n'est qu'une étiquette : MS-notifications ne l'interprète pas.

**Cette queue n'est pas déclarée dans `app/core/topology.py`**, qui reste le miroir strict de MS-aom-agregator. Elle l'est par le worker au démarrage (`app/run_worker.py`), car `broker.publish` ne déclare rien : sans ça, un résultat traité avant le premier démarrage de MS-notifications perdrait sa notification, le message étant non routable. Ses paramètres (`durable`, rien d'autre) reproduisent ceux du `src/main.ts` de MS-notifications ; toute divergence provoquerait un `PRECONDITION_FAILED`.

Contrairement à `retriggerAggregation`, la publication suit ici le changement de statut et son échec est avalé, simplement logué. Le statut est déjà en base à ce moment-là : laisser remonter l'exception ferait rejeter le message d'ingestion sans remise en file, perdant l'accusé pour une notification manquée. Un réseau introuvable ne déclenche aucune notification.

## Stack

| Brique | Choix | À savoir |
|---|---|---|
| Web | FastAPI + uvicorn | Le broker est connecté dans le `lifespan` |
| GraphQL | Strawberry, fédération 2.0 | `federation_version` épinglé à `"2.0"` alors que la lib supporte 2.11 |
| Base | MongoDB via motor | Async, aucun ODM, dictionnaires bruts |
| Messagerie | FastStream 0.6 + RabbitMQ | En 0.6, `disconnect()` n'existe plus, c'est `stop()` |
| HTTP sortant | httpx | Un seul client externe, data.gouv |
| Config | pydantic-settings | Deux sources séparées, voir ci-dessous |
| Dépendances | uv + `uv.lock` | Le venv est hors du projet, dans `/opt/venv` |
| Lint | ruff | Déclaré en dépendance, sans configuration ni CI |

### Deux fichiers de configuration, deux rôles

`app/core/config.py` déclare deux classes qui lisent deux fichiers différents. Confusion fréquente.

| Classe | Fichier | Contenu |
|---|---|---|
| `Secrets` | `.env`, non versionné | `DATABASE_URL`, `RABBITMQ_URL`, `TRANSPORT_DATA_GOUV_API_TOKEN` |
| `Properties` | `application.properties`, versionné | `APP_NAME`, `LOG_LEVEL`, `GRAPHQL_PREFIX`, URL de data.gouv |

Les variables d'environnement priment sur les deux : le compose surcharge `RABBITMQ_URL` pour pointer sur l'alias `rabbitmq` du réseau partagé.

## Démarrer depuis un clone neuf

> **Premier obstacle, immédiat.** Le `Dockerfile` contient `COPY pyproject.toml uv.lock .env ./`. Le fichier `.env` étant dans le `.gitignore`, un clone frais n'en a pas et `docker compose up` échoue au build sur un fichier introuvable. Il n'existe aucun `.env.example` pour indiquer quoi y mettre.

1. Créer le réseau Docker partagé, s'il n'existe pas. Il est déclaré `external` par tous les composes du monorepo.

   ```bash
   docker network create hubert-network
   ```

2. Écrire le `.env` à la racine du dépôt, avec ces trois clés :

   ```
   DATABASE_URL=mongodb://mongouser:mongopassword@mongodb-admin:27017
   RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
   TRANSPORT_DATA_GOUV_API_TOKEN=
   ```

   Le token peut rester vide, l'endpoint data.gouv utilisé est public. Le nom d'hôte Mongo est le `container_name`, pas le nom de service : c'est celui qui est garanti unique sur un réseau partagé entre plusieurs projets compose.

3. Démarrer RabbitMQ, qui vit dans le compose de la racine du monorepo et non ici :

   ```bash
   docker compose -f ../../docker-compose.yml up -d rabbitmq
   ```

4. Lancer les trois conteneurs du service — `mongodb-admin`, `service_admin`, `ms-admin-worker` :

   ```bash
   docker compose up -d
   ```

5. Vérifier que le worker écoute. La ligne attendue nomme la queue :

   ```bash
   docker logs ms-admin-worker | grep "waiting for messages"
   ```

6. Interroger le subgraph en direct, sans passer par la gateway. GraphiQL est servi sur `http://localhost:8001/graphql`.

   ```bash
   curl -s -X POST http://localhost:8001/graphql -H 'Content-Type: application/json' -d '{"query":"{ getRegistredTransitNetworks(limit:5){ totalCount items { name status statusLabel } } }"}'
   ```

7. Fermer la boucle sans dépendre de l'agrégateur, en simulant un accusé d'ingestion :

   ```bash
   docker exec ms-admin-worker python -m app.test_ingestion_publisher <external_id> ok
   ```

8. Suivre le mail envoyé à l'admin. Quatre lignes jalonnent la chaîne, mais une seule atteste d'un envoi SMTP réel, celle de `SmtpMailProvider` :

   ```bash
   docker logs ms-admin-worker | grep "Notification admin"
   docker logs service-notifications | grep -E "notification_requested|E-mail envoyé|Livraison"
   ```

   **`Livraison "EMAIL" réussie` ne prouve pas qu'un mail est parti.** Si `SMTP_HOST` est vide côté MS-notifications, `SmtpMailProvider` logue `SMTP_HOST absent : e-mail à … non envoyé` et rend la main sans erreur : le consumer considère la livraison réussie. C'est `E-mail envoyé à …` qu'il faut chercher.

### Après toute modification du schéma

Le router Apollo valide chaque requête contre `gateway/supergraph.graphql`, un fichier statique chargé au démarrage. Il n'introspecte rien à l'exécution. Ajouter un champ ou une mutation ici les rend disponibles sur le port 8001 mais **invisibles depuis la gateway** tant que le supergraph n'est pas recomposé. Le symptôme est un `GRAPHQL_VALIDATION_FAILED` côté front alors que tout fonctionne en direct.

```bash
make supergraph   # depuis la racine du monorepo
```

La recomposition introspecte les sept subgraphs et échoue si un seul manque à l'appel : ils doivent tous être démarrés.

## Tests

La suite tourne entièrement hors ligne : MongoDB, RabbitMQ et l'API
transport.data.gouv sont simulés en mémoire, aucun conteneur n'est nécessaire.

```bash
uv sync --group dev
uv run ruff check .
uv run pytest --cov
```

Le seuil de couverture (85 %) et les fichiers exclus sont définis dans
`pyproject.toml`. La CI (`.github/workflows/ci.yml`) exécute exactement ces
commandes.

Les bugs connus et non corrigés sont documentés par des tests
`xfail(strict=True)` : quand un bug est corrigé, son test passe, la suite
échoue, et il faut retirer le marqueur `xfail`.