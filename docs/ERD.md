# Entity Relationship Diagram

This diagram reflects the current Django models in `backend/warehouse`.

```mermaid
erDiagram
    Client ||--o{ Batch : has
    DeviceModel ||--o{ ModelVersion : has
    ModelVersion ||--o{ Batch : "linked via"
    DeviceModel ||--o{ Device : has
    ModelVersion ||--o{ Device : has
    Batch ||--o{ Device : contains

    Client {
        int id PK
        string client_name UK
        string client_status "default Active"
    }

    DeviceModel {
        int id PK
        string model_name "intentionally not unique"
        string model_status "default Active"
    }

    ModelVersion {
        int id PK
        int model_id FK
        string version
        string status "default Active"
    }

    Batch {
        int id PK
        string batch_code UK
        int client_id FK
        int model_version_id FK
    }

    DeviceStaging {
        int id PK
        string serial_number UK
        string model_name "denormalized"
        string version_name "denormalized"
        string batch_code "denormalized"
        string client_name "denormalized"
        string status "default PENDING"
        text error_message
        datetime created_at
    }

    Device {
        int id PK
        string serial_number UK
        int model_id FK
        int version_id FK
        int batch_id FK
        string device_status "ACTIVE | SCRAPPED | DECOMMISSIONED"
        datetime created_at
    }
```

## Notes

- **DeviceStaging** intentionally avoids foreign keys during scan/validation; confirmed devices are promoted to **Device** with proper FK relationships.
- **Client**, **DeviceModel**, and **ModelVersion** use status fields instead of hard deletes to preserve audit history.
- **Batch** ties a client to a model version under a unique `batch_code`.
- **DeviceModel.model_name** is intentionally not unique — the same model name can exist across different clients; uniqueness is enforced at the `ModelVersion` level via `unique_together (model, version)`.