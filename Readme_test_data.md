## Testing the system

Once the system is running, you can build a small test dataset through the UI by following the steps below. All names and codes are fictional.

### 1. Log in

On the login page, use the **Demo Access** panel: click a department to auto-fill its credentials, then *Sign in*. No account setup is needed.

**Scope:** the Warehouse module is fully working, so use **Warehouse** for the steps below. Repairs, Stores and Finance are designed (see `/docs`) but not yet implemented. You can still sign in as them to see department-based access control: they cannot open Warehouse screens.

### 2. Test data

**Clients** (step 1)

| Client          |
|-----------------|
| Demo Service Co |
| Alpha Retail    |
| Beacon Foods    |
| Cedar Pharmacy  |

Demo Service Co stands in for the servicing company. Only its devices can be rented out.

**Batches** (step 2)

| Batch code | Client          | Model      | Version | Devices to scan |
|------------|-----------------|------------|---------|-----------------|
| DEMO001    | Demo Service Co | Terminal X | v1      | 6               |
| DEMO002    | Alpha Retail    | Terminal X | v1      | 3               |
| DEMO003    | Beacon Foods    | Terminal Y | v1      | 3               |

DEMO001 creates the model and version. DEMO002 reuses the same model and version, so select them from the dropdown instead of typing them again.

The device counts are only a suggestion. There is no limit on how many devices you can scan per batch, so feel free to scan more.

**Serial numbers** follow `<batch_code>-<device_id>`:

- DEMO001: `DEMO001-01` to `DEMO001-06`
- DEMO002: `DEMO002-01` to `DEMO002-03`
- DEMO003: `DEMO003-01` to `DEMO003-03`

**Rentals** (used in step 4). Dates are relative to the day you test:

| Device       | Rented to      | Start date   | Expected return |
|--------------|----------------|--------------|-----------------|
| `DEMO001-01` | Alpha Retail   | today - 20 d | today + 40 d    |
| `DEMO001-02` | Beacon Foods   | today - 55 d | today + 5 d     |
| `DEMO001-03` | Cedar Pharmacy | today - 90 d | today - 7 d     |

### 3. Build the data

Warehouse → Clients & Batches. The workflow has three steps:

1. **Client creation:** add the clients from the table above and save.
2. **Linking:** select a client, then create the batch with its model and version.
   - New model or version: type it, and enter the batch code.
   - Model and version that already exist: select them from the dropdown.
   - Do this for all three batches.
3. **Device scanning:** scan or type the batch's serial numbers. Each scan is validated by the system and saved immediately, so there is no confirm or save step. The screen shows a running count and lists only exceptions (bad format, unknown batch code, duplicate SN).

Try a duplicate: scan `DEMO001-01` again. It is reported as already saved, and nothing is duplicated.

### 4. Rentals

1. **Assign Rental:** choose the client, scan the serial numbers from the rentals table, set the dates, and submit.
2. **Guards to try:**
   - Rent `DEMO001-01` a second time: rejected (one active rental per device).
   - Rent `DEMO002-01`: rejected (client-owned, not rentable).
3. **End Rental:** scan `DEMO001-01`, review the active rental that appears, and pick an end date.

### 5. Tests

```bash
python manage.py test        # backend, including the rental suite
npx playwright test          # end-to-end
```

### Resetting

To start over with a clean database: `docker compose down -v`, then restart and run migrations again.